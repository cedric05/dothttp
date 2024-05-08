import json
import logging
import os
import pickle
import subprocess
import time

import msal
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.serialization import pkcs12
from requests.auth import AuthBase
from requests.models import PreparedRequest

from ..exceptions import DothttpAzureAuthException
from ..models.parse_models import (
    AzureAuthCertificate,
    AzureAuthSP,
    AzureAuthType,
    AzureAuthWrap,
)

AZURE_CLI_TOKEN_STORE_PATH = os.path.expanduser("~/.dothttp.azure-cli.pkl")

AZURE_SP_TOKEN_STORE_PATH = os.path.expanduser("~/.dothttp.msal_token_cache.pkl")

request_logger = logging.getLogger("request")


def load_private_key_and_thumbprint(cert_path, password=None):
    extension = os.path.splitext(cert_path)[1].lower()
    with open(cert_path, "rb") as cert_file:
        cert_data = cert_file.read()

    if extension == ".pem":
        private_key = serialization.load_pem_private_key(
            cert_data, password, default_backend()
        )
        cert = x509.load_pem_x509_certificate(cert_data, default_backend())
    elif extension == ".cer":
        cert = x509.load_der_x509_certificate(cert_data, default_backend())
        private_key = None  # .cer files do not contain private key
    elif extension == ".pfx" or extension == ".p12":
        private_key, cert, _ = pkcs12.load_key_and_certificates(
            cert_data, password, default_backend()
        )
    else:
        raise ValueError(f"Unsupported certificate format {extension}")

    if private_key is not None:
        private_key_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    else:
        private_key_bytes = None

    thumbprint = cert.fingerprint(hashes.SHA1()).hex()

    return private_key_bytes, thumbprint


# Azure Cli Auth uses the 'az' command to generate an access_token.
# In Windows, Azure Cli checks for an azure-cli package update availability and, if an update is found, it prompts for input.
# When using 'cmd' in Windows, it opens a new terminal, which lets Azure Cli think that a tty is available and prompts for input,
# leading to hanging requests.
# It is advised to set `az config set auto-upgrade.enable=no` and update Azure Cli manually for Dothttp to work properly.
class AzureAuth(AuthBase):
    def __init__(self, azure_auth_wrap: AzureAuthWrap):
        self.azure_auth_wrap = azure_auth_wrap
        self.token_cache = msal.SerializableTokenCache()
        try:
            # Try to load the token cache from a file
            with open(AZURE_SP_TOKEN_STORE_PATH, "rb") as token_cache_file:
                self.token_cache.deserialize(json.dumps(pickle.load(token_cache_file)))
        except FileNotFoundError:
            # If the file does not exist, initialize a new token cache
            pass

    def __call__(self, r: PreparedRequest) -> PreparedRequest:
        try:
            if self.azure_auth_wrap.azure_auth_type == AzureAuthType.SERVICE_PRINCIPAL:
                self.acquire_token_silently_or_ondemand(
                    r, self.azure_auth_wrap.azure_spsecret_auth
                )
                self.save_token_cache()
            elif self.azure_auth_wrap.azure_auth_type == AzureAuthType.CERTIFICATE:
                self.acquire_token_silently_or_ondemand(
                    r, self.azure_auth_wrap.azure_spcert_auth
                )
                self.save_token_cache()
            # For device code and cli authentication, we use the access token directly
            # in future we can use msal to get the access token for device code
            elif self.azure_auth_wrap.azure_auth_type in [
                AzureAuthType.CLI,
                AzureAuthType.DEVICE_CODE,
            ]:
                self.acquire_token_from_azure_cli(r)
        except (KeyError, Exception) as ex:
            raise DothttpAzureAuthException(
                message=f"unable to acquire access_token. Failed with error {ex}"
            )
        return r

    def acquire_token_from_azure_cli(self, r):
        access_token = None
        expires_on = None
        # Try to load the access token and its expiry time from a file
        scope = (
            self.azure_auth_wrap.azure_cli_auth.scope
            if self.azure_auth_wrap.azure_cli_auth
            else self.azure_auth_wrap.azure_device_code.scope
        )

        if os.path.exists(AZURE_CLI_TOKEN_STORE_PATH):
            request_logger.debug("azure cli token already exists, using")
            with open(AZURE_CLI_TOKEN_STORE_PATH, "rb") as token_file:
                data = pickle.load(token_file)
                scope_wise_store = data.get(scope, {})
                access_token = scope_wise_store.get("access_token", None)
                expires_on = scope_wise_store.get("expires_on", None)
            # Get the current time in seconds since the Epoch
        current_time = time.time()

        # If the file does not exist or the token has expired, get a new access token
        if not access_token or not expires_on or current_time >= expires_on:
            request_logger.debug(
                "azure cli token store cached not availabile or expired"
            )
            # get token from cli by invoking az account get-access-token
            cmd = "az"
            if os.name == "nt":
                cmd = "az.cmd"
            result = subprocess.run(
                [cmd, "account", "get-access-token", "--scope", scope],
                capture_output=True,
                text=True,
            )
            result_json = json.loads(result.stdout)
            access_token = result_json["accessToken"]
            # Convert the expiresOn field to seconds since the Epoch
            expires_on = time.mktime(
                time.strptime(result_json["expiresOn"], "%Y-%m-%d %H:%M:%S.%f")
            )
            # Save the new access token and its expiry time to the file
            with open(AZURE_CLI_TOKEN_STORE_PATH, "wb") as token_file:
                scope_wise_store = dict()
                scope_wise_store[scope] = {
                    "access_token": access_token,
                    "expires_on": expires_on,
                }
                pickle.dump(scope_wise_store, token_file)
        request_logger.debug(
            "computed or fetched azure cli token access bearer token and appeneded"
        )
        r.headers["Authorization"] = f"Bearer {access_token}"

    def acquire_token_silently_or_ondemand(self, r, auth_wrap: AzureAuthSP):
        kwargs = {
            "client_id": auth_wrap.client_id,
            "authority": f"https://login.microsoftonline.com/{auth_wrap.tenant_id}",
            "token_cache": self.token_cache,
        }
        if isinstance(auth_wrap, AzureAuthCertificate):
            try:
                private_key_bytes, thumbprint = load_private_key_and_thumbprint(
                    auth_wrap.certificate_path, auth_wrap.certificate_password
                )
                kwargs["client_credential"] = {
                    "private_key": private_key_bytes,
                    "thumbprint": thumbprint,
                }
            except Exception as e:
                request_logger.error("loading private key failed with error", e)
                raise DothttpAzureAuthException(message=str(e))
        else:
            kwargs["client_credential"] = auth_wrap.client_secret
        app = self.create_confidential_app(kwargs)
        accounts = app.get_accounts()
        if accounts:
            result = app.acquire_token_silent(
                scopes=[auth_wrap.scope], account=accounts[0]
            )
        if not accounts or "access_token" not in result:
            result = app.acquire_token_for_client(scopes=[auth_wrap.scope])
        r.headers["Authorization"] = f"Bearer {result['access_token']}"

    def create_confidential_app(self, kwargs):
        return msal.ConfidentialClientApplication(**kwargs)

    def save_token_cache(self):
        with open(AZURE_SP_TOKEN_STORE_PATH, "wb") as token_cache_file:
            pickle.dump(json.loads(self.token_cache.serialize()), token_cache_file)

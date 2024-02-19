import os
import unittest
from unittest.mock import MagicMock, patch

from requests import PreparedRequest

from dothttp.auth.azure_auth import AzureAuth
from dothttp.models.parse_models import AzureAuthServicePrincipal
from dothttp.models.parse_models import AzureAuthWrap, AzureAuthType
from dothttp.parse.request_base import HttpFileFormatter  # replace with your actual module
from test import TestBase

dir_path = os.path.dirname(os.path.realpath(__file__))
base_dir = f"{dir_path}/requests"
filename = f"{base_dir}/azureauth.http"



class TestDothttpLoading(TestBase):
    """Tests for `azure_auth.py`."""


    def base(
            self,
            target,
            auth_wrap_type: AzureAuthType,
            **kwargs):
        tenant_id = kwargs.get("tenant_id", "dummy_tenant")
        client_id = kwargs.get("client_id", "dummy_client")
        secret_value = kwargs.get("secret_value", "dummy_secret")
        certificate_path = kwargs.get("certificate_path", "dummy_certificate_path")
        scope = kwargs.get("scope", "dummy_scope")
        properties = kwargs.get("properties", [])
        request = self.get_req_comp(file=filename, properties=properties, target=target)
        request.load()
        request.load_def()
        auth: AzureAuth = request.httpdef.auth
        self.assertEqual(
            auth_wrap_type,
            auth.azure_auth_wrap.azure_auth_type,
            "auth type is different from expected")
        if auth_wrap_type == AzureAuthType.SERVICE_PRINCIPAL:
            self.assertEqual(
                tenant_id,
                auth.azure_auth_wrap.azure_spsecret_auth.tenant_id,
                "tenant_id is different from expected")
            self.assertEqual(
                client_id,
                auth.azure_auth_wrap.azure_spsecret_auth.client_id,
                "client_id is different from expected")
            self.assertEqual(
                secret_value,
                auth.azure_auth_wrap.azure_spsecret_auth.client_secret,
                "secret_value is different from expected")
            self.assertEqual(
                scope,
                auth.azure_auth_wrap.azure_spsecret_auth.scope,
                "scope is different from expected")
        elif auth_wrap_type == AzureAuthType.CERTIFICATE:
            self.assertEqual(
                tenant_id,
                auth.azure_auth_wrap.azure_spcert_auth.tenant_id,
                "tenant_id is different from expected")
            self.assertEqual(
                client_id,
                auth.azure_auth_wrap.azure_spcert_auth.client_id,
                "client_id is different from expected")
            self.assertEqual(
                certificate_path,
                auth.azure_auth_wrap.azure_spcert_auth.certificate_path,
                "certificate_path is different from expected")
            self.assertEqual(
                scope,
                auth.azure_auth_wrap.azure_spcert_auth.scope,
                "scope is different from expected")
        elif auth_wrap_type == AzureAuthType.CLI:
            self.assertEqual(
                scope,
                auth.azure_auth_wrap.azure_cli_auth.scope,
                "scope is different from expected")
        return request
    def test_azure_auth_load(self):
        """Test azure_auth."""
        properties = ["tenant_id=dummy_tenant", 
                        "client_id=dummy_client",
                        "secret_value=dummy_secret", 
                        "scope=dummy_scope",
                        "certificate_path=dummy_certificate_path"
                    ]
        self.base("azure_sp", AzureAuthType.SERVICE_PRINCIPAL, properties=properties, )
        self.base("azure_cert", AzureAuthType.CERTIFICATE, properties=properties)
        self.base("azure_cli", AzureAuthType.CLI, properties=properties)


class TestAzureAuth(unittest.TestCase):
    @patch('msal.application.ConfidentialClientApplication')  # replace with your actual module
    def test_service_principal_auth(self, MockConfidentialClientApplication):
        # Setup
        mock_app = MockConfidentialClientApplication.return_value
        mock_app.acquire_token_for_client.return_value = {'access_token': 'test_token', 'expires_in': 3600}
        
        azure_auth = AzureAuth(
            azure_auth_wrap=AzureAuthWrap(
                azure_auth_type=AzureAuthType.SERVICE_PRINCIPAL, 
                azure_spsecret_auth=AzureAuthServicePrincipal(
                    tenant_id="tenant_id", 
                    client_id="client_id",
                    client_secret="client_secret",
                    scope="https://management.azure.com/.default")
                )
            )

        azure_auth.create_confidential_app = MagicMock(return_value=mock_app)

        r = PreparedRequest()
        r.prepare_headers({})
        
        azure_auth(r)
        
        # Verify
        self.assertEqual(r.headers['Authorization'], 'Bearer test_token')

        mock_app.acquire_token_for_client.assert_called_once_with(scopes=['https://management.azure.com/.default'])
        mock_app.get_accounts.assert_called_once() # This is called to get cached token

        mock_app.get_accounts.return_value = [None]
        mock_app.acquire_token_silent.return_value =  {'access_token': 'test_token2', 'expires_in': 3600}
        azure_auth(r)
        self.assertEqual(r.headers['Authorization'], 'Bearer test_token2')


class TestAzureEnd2End(TestBase):
    @patch('msal.application.ConfidentialClientApplication')  # replace with your actual module
    def test_service_principal_auth(self, MockConfidentialClientApplication):
        # Setup
        mock_app = MockConfidentialClientApplication.return_value
        mock_app.acquire_token_for_client.return_value = {'access_token': 'test_token', 'expires_in': 3600}
        mock_app.get_accounts.return_value = [None]
        mock_app.acquire_token_silent.return_value =  {'access_token': 'test_token2', 'expires_in': 3600}
        
        # set variables
        properties = ["tenant_id=dummy_tenant", 
                        "client_id=dummy_client",
                        "secret_value=dummy_secret", 
                        "scope=dummy_scope",
                        "certificate_path=dummy_certificate_path"
                    ]
        # get request from parsing file
        req_comp = self.get_req_comp(file=filename, properties=properties, target="azure_sp")
        # load http_def
        req_comp.load_def()

        # mock create_confidential_app
        req_comp.httpdef.auth.create_confidential_app = MagicMock(return_value=mock_app)
        
        # get prepared request
        prep_req = req_comp.get_request()
        # Verify
        
        # verify token is fetched from cache
        mock_app.acquire_token_silent.assert_called_once_with(scopes=['dummy_scope'], account=None)
        # verify acquire token not called
        mock_app.acquire_token_for_client.assert_not_called()

        # verify token generated from acquire token silent is used
        self.assertEqual(prep_req.headers['Authorization'], 'Bearer test_token2')
        mock_app.get_accounts.return_value = []

        # verify http file format generation (which does not substitute variables)
        self.assertEqual("""@name("azure_sp")
GET "https://management.azure.com/"
azurespsecret(tenant_id="{{tenant_id}}", client_id="{{client_id}}", client_secret="{{secret_value}}", scope="{{scope}}")


""", HttpFileFormatter.format_http(req_comp.http))


        # verify variable substitution by using http_def (which substitutes variables)
        self.assertEqual("""@name("azure_sp")
GET "https://management.azure.com/"
azurespsecret(tenant_id="dummy_tenant", client_id="dummy_client", client_secret="dummy_secret", scope="dummy_scope")



""", HttpFileFormatter.format_http(req_comp.httpdef.get_http_from_req()))
        




        
        




    # Add more test methods for AzureAuthCertificate and AzureAuthCli
if __name__ == '__main__':
    unittest.main()
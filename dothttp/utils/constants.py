import logging

MIME_TYPE_JSON = "application/json"
FORM_URLENCODED = "application/x-www-form-urlencoded"
MULTIPART_FORM_INPUT = "multipart/form-data"
TEXT_PLAIN = "text/plain"
CONTENT_TYPE = "content-type"

UNIX_SOCKET_SCHEME = "http+unix"

BASEIC_AUTHORIZATION_HEADER = "Authorization"


base_logger = logging.getLogger("dothttp")
request_logger = logging.getLogger("request")
curl_logger = logging.getLogger("curl")


try:
    from requests_aws4auth import AWS4Auth
except ImportError:
    AWS4Auth = None
try:
    from requests_ntlm import HttpNtlmAuth
except ImportError:
    HttpNtlmAuth = None

try:
    import jstyleson as json
    from jsonschema import validate
except ImportError:
    import json

    validate = None

try:
    from ..auth.azure_auth import AzureAuth
except:
    # this is for dothttp-wasm, where msal most likely not installed
    AzureAuth = None

try:
    import magic
except ImportError:
    magic = None

try:
    from requests_hawk import HawkAuth as RequestsHawkAuth
except BaseException:
    RequestsHawkAuth = None

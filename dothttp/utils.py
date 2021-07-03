import os
import xml.etree.ElementTree as ET

from requests.auth import AuthBase
from requests.models import to_key_val_list, PreparedRequest
from suds.wsse import *

APPLICATION_JSON = "application/json"
CONTENT_TYPE = "content-type"


def get_real_file_path(path='http.tx', current_file=__file__, ):
    if os.path.exists(current_file):
        tx_model_path = os.path.join(os.path.dirname(os.path.abspath(current_file)), path)
    else:
        tx_model_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(current_file))), path)
    return tx_model_path


def triple_or_double_tostring(list_of_triple_or_double, update_content_func):
    return "".join(
        [update_content_func(i.triple[3:-3]) if i.triple else update_content_func(i.str) for i in
         list_of_triple_or_double])


class SoapAuthRequests(AuthBase):

    def __init__(self, username, password):
        self.username = username
        self.password = password

    def __call__(self, r: PreparedRequest):
        security = Security()
        token = UsernameToken(self.username, self.password)
        security.tokens.append(token)
        soap_security_header = security.xml()
        tree = ET.fromstring(r.body)


def quote_or_unquote(line: str):
    if '"' in line and "'" in line:
        return '"', line.replace("'", "\\'")
    elif '"' in line:
        return "'", line
    else:
        return '"', line


def json_to_urlencoded_array(data):
    # copied from
    # https://github.com/psf/requests/blob/1466ad713cf84738cd28f1224a7ab4a19e50e361/requests/models.py#L97-L105
    # although i don't want to copy this function
    # but by doing encoding and decoding is not approach
    result = []
    for k, vs in to_key_val_list(data):
        if isinstance(vs, (str, bytes)) or not hasattr(vs, '__iter__'):
            vs = [vs]
        for v in vs:
            if v is not None:
                result.append((k, v))
    return result

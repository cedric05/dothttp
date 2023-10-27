import os
import unittest

from dothttp import AWS4Auth
from test import TestBase

dir_path = os.path.dirname(os.path.realpath(__file__))
base_dir = f"{dir_path}/requests"
filename = f"{base_dir}/awsauth.http"


class AwsAuthUnit(TestBase):

    def base(
            self,
            params,
            service='s3',
            region='us-east-1',
            access_id='dummy',
            secret_key='dummy'):
        request = self.get_req_comp(file=filename, **params)
        request.load()
        request.load_def()
        auth: AWS4Auth = request.httpdef.auth
        self.assertEqual(
            service,
            auth.service,
            "service is different from expected")
        self.assertEqual(
            region,
            auth.region,
            "region is different from expected")
        self.assertEqual(
            secret_key,
            auth.signing_key.secret_key,
            "secret_key is different from expected")
        self.assertEqual(
            access_id,
            auth.access_id,
            "access_id is different from expected")
        return request

    def test_simple(self):
        self.base(
            params=dict(
                target="simple"),
            service="s3",
            region='us-east-1')

    def test_resolve_properties(self):
        properties = {
            "access_id": 'dummy2',
            "secret_key": "dummy2",
            "service": "s3",
            "region": "region2"
        }
        prop = [f"{i}={j}" for i, j in properties.items()]
        self.base(params=dict(target="resolve properties",
                              properties=prop
                              ),
                  **properties)

    def test_resolve_properties_with_default(self):
        self.base(params=dict(target="resolve properties with default"))

    def test_extend(self):
        self.base(params=dict(target="extend"))

    def test_extend2(self):
        request = self.base(params=dict(target="extend2"))
        self.assertEqual("http://s3.amazonaws.com/some", request.httpdef.url)

    def test_extend3(self):
        properties = {
            "access_id": 'dummy2',
            "secret_key": "dummy2",
            "service": "s3",
            "region": "region2"
        }
        prop = [f"{i}={j}" for i, j in properties.items()]
        self.base(params=dict(target="extend", properties=prop), **properties)

    def test_default_region(self):
        self.base(params=dict(target="default us-east-1 region optional", ),
                  )

    def test_region_from_url(self):
        self.base(
            params=dict(
                target="region from url and s3"),
            region='eu-west-1')

    def test_no_service_and_no_region(self):
        self.base(
            params=dict(
                target="service from url and region defaulted to us-east-1"))

    def test_no_service_and_no_region_with_extra_url(self):
        self.base(
            params=dict(
                target="region and service from url with bucket id"))

    def test_legacy_url_with_noservice_noregion(self):
        self.base(params=dict(target="region and service with legacy url"))

    def test_fix_region_and_service_from_url(self):
        self.base(params=dict(target="fix region and service from url"))

    def test_fix_region_and_service_from_url2(self):
        self.base(params=dict(target="fix region and service from url2"))

    def test_auth_headers_get(self):
        reqcomp = self.base(params=dict(target="with-x-amz-date header"))
        request = reqcomp.get_request()
        self.assertEqual(
            {
                'x-amz-date': '20210817T103121Z',
                'x-amz-content-sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
                'Authorization': 'AWS4-HMAC-SHA256 Credential=dummy/20210817/us-east-1/s3/aws4_request, SignedHeaders=host;x-amz-content-sha256;x-amz-date, Signature=bb4e6ae21b8667877f23b0f2b08bb54209ee6c5f120965f96398e45caf83fa23'},
            request.headers)

    def test_auth_headers_post(self):
        reqcomp = self.base(
            params=dict(
                target="with-x-amz-date header with post data"),
            service="ecr")
        request = reqcomp.get_request()
        self.assertEqual(
            {
                'X-Amz-Target': 'AmazonEC2ContainerRegistry_V20150921.DescribeRegistry',
                'Content-Type': 'application/x-amz-json-1.1',
                'x-amz-date': '20210817T103121Z',
                'Content-Length': '2',
                'x-amz-content-sha256': '44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a',
                'Authorization': 'AWS4-HMAC-SHA256 Credential=dummy/20210817/us-east-1/ecr/aws4_request, SignedHeaders=content-type;host;x-amz-content-sha256;x-amz-date;x-amz-target, Signature=1d236ae264049a0b7e6c8374d053d824f6f5ccf6b183677d15791b3b98f663ee'},
            request.headers)


if __name__ == '__main__':
    unittest.main()

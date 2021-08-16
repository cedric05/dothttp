import os
import unittest

from requests_aws4auth import AWS4Auth

from test import TestBase

dir_path = os.path.dirname(os.path.realpath(__file__))
base_dir = f"{dir_path}/requests"
filename = f"{base_dir}/awsauth.http"


class AwsAuthUnit(TestBase):

    def base(self, params, service='s3', region='us-east-1', access_id='dummy', secret_key='dummy'):
        request = self.get_req_comp(file=filename, **params)
        request.load()
        request.load_def()
        auth: AWS4Auth = request.httpdef.auth
        self.assertEqual(service, auth.service, "service is different from expected")
        self.assertEqual(region, auth.region, "region is different from expected")
        self.assertEqual(secret_key, auth.signing_key.secret_key, "secret_key is different from expected")
        self.assertEqual(access_id, auth.access_id, "access_id is different from expected")
        return request

    def test_simple(self):
        self.base(params=dict(target="simple"), service="s3", region='us-east-1')

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
        self.base(params=dict(target="region from url and s3"), region='eu-west-1')

    def test_no_service_and_no_region(self):
        self.base(params=dict(target="service from url and region defaulted to us-east-1"))

    def test_no_service_and_no_region_with_extra_url(self):
        self.base(params=dict(target="region and service from url with bucket id"))

    def test_legacy_url_with_noservice_noregion(self):
        self.base(params=dict(target="region and service with legacy url"))

    def test_fix_region_and_service_from_url(self):
        self.base(params=dict(target="fix region and service from url"))

    def test_fix_region_and_service_from_url2(self):
        self.base(params=dict(target="fix region and service from url2"))


if __name__ == '__main__':
    unittest.main()

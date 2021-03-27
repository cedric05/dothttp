import json
from unittest import TestCase
from urllib.parse import parse_qs

from requests import PreparedRequest

from dothttp import property_util
from test import TestBase
from test.core.test_request import dir_path

base_dir = f"{dir_path}/substitution"


class TestRandoms(TestCase):
    def test_random_int(self):
        self.assertTrue(property_util.get_random_int())
        self.assertTrue(property_util.get_random_int(0))
        self.assertTrue(property_util.get_random_int(10))
        self.assertTrue(10 <= property_util.get_random_int(2) < 100)
        self.assertTrue(100 <= property_util.get_random_int(3) < 1000)

    def test_random_float(self):
        self.assertTrue(property_util.get_random_float())
        self.assertTrue(property_util.get_random_float(None))

    def test_random_str(self):
        self.assertTrue(property_util.get_random_str())
        self.assertEqual(10, len(property_util.get_random_str(10)))
        self.assertEqual(2, len(property_util.get_random_str(2)))

    def test_random_bool(self):
        random_bool = property_util.get_random_bool()


class SubstitutionTest(TestBase):
    def test_basic(self):
        int_request: PreparedRequest = self.get_request(file=f'{base_dir}/random.http', target='int')
        int_payload = json.loads(int_request.body)
        intValue = int(int_payload['test'])
        self.assertTrue(100 <= intValue < 1000, f'value is {intValue}')
        self.assertTrue(int(int_payload['test2']))

        bool_request: PreparedRequest = self.get_request(file=f'{base_dir}/random.http', target=2)
        trueOrFalse = json.loads(bool_request.body)['test']
        self.assertTrue(trueOrFalse == True or trueOrFalse == False)

        str_request: PreparedRequest = self.get_request(file=f'{base_dir}/random.http', target='str')
        data = json.loads(str_request.body)
        self.assertTrue(10 == len(data['test']), f'this is skeptical {str_request.body}')
        self.assertTrue(1 < len(data['test2']) <= 10, data['test2'])

        float_request: PreparedRequest = self.get_request(file=f'{base_dir}/random.http', target='float')
        request_data = json.loads(float_request.body)
        self.assertTrue(float(request_data['test']))

        float_request2: PreparedRequest = self.get_request(file=f'{base_dir}/random.http', target='random+string')
        request_data = json.loads(float_request2.body)
        self.assertTrue(request_data['test2'].endswith('@gmail.com'))
        self.assertTrue(request_data['test2'], request_data['test4'])
        self.assertTrue(request_data['test2'], request_data['test4'])

    def test_complex(self):
        should_load_basic: PreparedRequest = self.get_request(file=f'{base_dir}/complexrandom.http', target=1)
        self.assertNotEqual("https://req.dothttp.dev/", should_load_basic.url)
        self.assertTrue(should_load_basic.url.startswith("https://req.dothttp.dev/"))

        json_reuse_request: PreparedRequest = self.get_request(file=f'{base_dir}/complexrandom.http', target='reuse')
        self.assertTrue(json_reuse_request.url.startswith("https://req.dothttp.dev/"))
        payload = json.loads(json_reuse_request.body)
        self.assertTrue(isinstance(payload['int'], int))
        self.assertTrue(isinstance(payload['bool'], bool))
        self.assertTrue(isinstance(payload['str'], str))
        self.assertTrue(isinstance(payload['float'], float))
        self.assertEqual(
            f"https://req.dothttp.dev/?int={payload['int']}&bool={'true' if payload['bool'] else 'false'}&str={payload['str']}&float={payload['float']}"
            , json_reuse_request.url)

        dataJsonreuse2: PreparedRequest = self.get_request(file=f'{base_dir}/complexrandom.http', target='reuse2')
        reuse2_str_value = parse_qs(dataJsonreuse2.body)['str'][0]
        self.assertEqual(f"https://req.dothttp.dev/?str={reuse2_str_value}", dataJsonreuse2.url)

        datareuse3: PreparedRequest = self.get_request(file=f'{base_dir}/complexrandom.http', target='reuse3')
        self.assertEqual(f"https://req.dothttp.dev/?str={datareuse3.body}", datareuse3.url)

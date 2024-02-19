import datetime
import json
from unittest import TestCase
from urllib.parse import parse_qs

from requests import PreparedRequest

from dothttp.utils import property_util
from test import TestBase
from test.core.test_request import dir_path

base_dir = f"{dir_path}/substitution"


class TestRandoms(TestCase):
    def test_random_int(self):
        self.assertTrue(property_util.get_random_int())
        self.assertTrue(property_util.get_random_int(0))
        self.assertTrue(property_util.get_random_int(10))
        self.assertTrue(10 <= property_util.get_random_int(2) <= 100)
        self.assertTrue(100 <= property_util.get_random_int(3) <= 1000)

    def test_random_float(self):
        self.assertTrue(property_util.get_random_float())
        self.assertTrue(property_util.get_random_float(None))

    def test_random_str(self):
        self.assertTrue(property_util.get_random_str())
        self.assertEqual(10, len(property_util.get_random_str(10)))
        self.assertEqual(2, len(property_util.get_random_str(2)))

    def test_random_bool(self):
        random_bool = property_util.get_random_bool()
        self.assertIn(random_bool, ['true', 'false'])

    def test_random_slug(self):
        slug = property_util.get_random_slug(3)
        self.assertTrue(slug.lower() == slug, 'slug lower should be slug')
        self.assertTrue('-' in slug, 'slug should contain atleast one `-`')

    def test_uuid(self):
        slug = property_util.get_uuid()
        self.assertTrue(36, len(slug))

    def test_timestamp(self):
        slug = property_util.get_timestamp()
        self.assertTrue(type(slug), int)
        self.assertAlmostEqual(int(datetime.datetime.now().timestamp()), slug)


class SubstitutionTest(TestBase):
    def test_basic(self):
        int_request: PreparedRequest = self.get_request(
            file=f'{base_dir}/random.http', target='int')
        int_payload = json.loads(int_request.body)
        int_value = int(int_payload['test'])
        print(f'int_value  {int_value} and int_payload {int_payload}')
        self.assertTrue(100 <= int_value < 1000, f'value is {int_value}')
        self.assertTrue(int(int_payload['test2']))

    def test_bool(self):
        bool_request: PreparedRequest = self.get_request(
            file=f'{base_dir}/random.http', target=2)
        trueOrFalse = json.loads(bool_request.body)['test']
        self.assertTrue(trueOrFalse or trueOrFalse == False)

    def test_str(self):
        str_request: PreparedRequest = self.get_request(
            file=f'{base_dir}/random.http', target='str')
        data = json.loads(str_request.body)
        self.assertTrue(10 == len(data['test']),
                        f'this is skeptical {str_request.body}')
        self.assertTrue(1 <= len(data['test2']) <= 10, data['test2'])

    def test_float(self):
        float_request: PreparedRequest = self.get_request(
            file=f'{base_dir}/random.http', target='float')
        request_data = json.loads(float_request.body)
        self.assertTrue(float(request_data['test']))

        float_request2: PreparedRequest = self.get_request(
            file=f'{base_dir}/random.http', target='random+string')
        request_data = json.loads(float_request2.body)
        self.assertTrue(request_data['test2'].endswith('@gmail.com'))
        self.assertTrue(request_data['test2'], request_data['test4'])
        self.assertTrue(request_data['test2'], request_data['test4'])

    def test_multiple_randoms(self):
        """
            Current test checks if property is defined random, it will pick first match and resolve accordingly.
            For rest of propertys, even if random is of bool or str or int (different from first match), resolution will be same as first
            usually one should always reuse and redeclare in dothttp unless prop is random
        """
        uuid_request: PreparedRequest = self.get_request(
            file=f'{base_dir}/random_double.http', target='double')
        request_data = json.loads(uuid_request.body)
        self.assertTrue(request_data['test_int'] == request_data['test_int2'])

    def test_uuid(self):
        # test uuid
        uuid_request: PreparedRequest = self.get_request(
            file=f'{base_dir}/random.http', target='uuid')
        request_data = json.loads(uuid_request.body)
        self.assertTrue('uuid' in request_data)
        self.assertEqual(36, len(request_data['uuid']))

    def test_slug(self):
        # test uuid
        slug_request: PreparedRequest = self.get_request(
            file=f'{base_dir}/random.http', target='slug')
        request_data = json.loads(slug_request.body)
        self.assertTrue('slug' in request_data)
        slug = request_data['slug']
        self.assertTrue(slug.lower() == slug, 'slug lower should be slug')
        self.assertTrue('-' in slug, 'slug should contain atleast one `-`')

    def test_timestamp(self):
        # test uuid
        timestamp_request: PreparedRequest = self.get_request(
            file=f'{base_dir}/random.http', target='timestamp')
        request_data = json.loads(timestamp_request.body)
        self.assertTrue('timestamp' in request_data)
        now = datetime.datetime.now()
        fromtimestamp = datetime.datetime.fromtimestamp(
            int(request_data['timestamp']))
        self.assertGreater(now, fromtimestamp)
        # self.assertLess((now - fromtimestamp).seconds, 4)
        self.assertAlmostEqual(int(now.timestamp()), request_data['timestamp'])

    def test_complex(self):
        should_load_basic: PreparedRequest = self.get_request(
            file=f'{base_dir}/complexrandom.http', target=1)
        self.assertNotEqual("https://req.dothttp.dev/", should_load_basic.url)
        self.assertTrue(should_load_basic.url.startswith(
            "https://req.dothttp.dev/"))

        json_reuse_request: PreparedRequest = self.get_request(
            file=f'{base_dir}/complexrandom.http', target='reuse')
        self.assertTrue(json_reuse_request.url.startswith(
            "https://req.dothttp.dev/"))
        payload = json.loads(json_reuse_request.body)
        self.assertTrue(isinstance(payload['int'], int))
        self.assertTrue(isinstance(payload['bool'], bool))
        self.assertTrue(isinstance(payload['str'], str))
        self.assertTrue(isinstance(payload['float'], float))
        self.assertTrue(isinstance(payload['time'], int))
        self.assertTrue(isinstance(payload['uuid'], str))
        self.assertTrue(isinstance(payload['slug'], str))

        # if not timestamp, raises
        datetime.datetime.fromtimestamp(payload['time'])
        self.assertTrue(36, len(payload['uuid']))
        self.assertTrue(payload['slug'].lower() == payload['slug'])

        self.assertEqual(
            f"https://req.dothttp.dev/?int={payload['int']}&bool={'true' if payload['bool'] else 'false'}&str={payload['str']}&float={payload['float']}",
            json_reuse_request.url)

        dataJsonreuse2: PreparedRequest = self.get_request(
            file=f'{base_dir}/complexrandom.http', target='reuse2')
        reuse2_str_value = parse_qs(dataJsonreuse2.body)['str'][0]
        self.assertEqual(
            f"https://req.dothttp.dev/?str={reuse2_str_value}",
            dataJsonreuse2.url)

        datareuse3: PreparedRequest = self.get_request(
            file=f'{base_dir}/complexrandom.http', target='reuse3')
        self.assertEqual(
            f"https://req.dothttp.dev/?str={datareuse3.body}",
            datareuse3.url)

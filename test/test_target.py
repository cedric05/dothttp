from test import TestBase
from test.test_request import dir_path

base_dir = f"{dir_path}/target"


class TestTarget(TestBase):

    def test_target_default(self):
        request = self.get_request(
            file=f"{base_dir}/default_target.http"
        )
        self.assertEqual("https://httpbin.org/get", request.url)

    def test_target_first_one_with_index(self):
        request = self.get_request(
            file=f"{base_dir}/default_target.http", target='1'
        )
        self.assertEqual("https://httpbin.org/get", request.url)

    def test_target_second_one_with_index(self):
        request = self.get_request(
            file=f"{base_dir}/default_target.http", target=2
        )
        self.assertEqual("https://httpbin.org/post", request.url)

    def test_target_with_names(self):
        # target with name
        first_target = self.get_request(
            file=f"{base_dir}/target_with_names_for_few.http", target="first"
        )
        self.assertEqual("https://req.dothttp.dev/get", first_target.url, "first target")

        # target second one with name
        second_target = self.get_request(
            file=f"{base_dir}/target_with_names_for_few.http", target="secondone"
        )
        self.assertEqual("https://req.dothttp.dev/post", second_target.url)
        self.assertEqual("hi=hi2", second_target.body)

        # target third one with index
        third_target = self.get_request(
            file=f"{base_dir}/target_with_names_for_few.http", target=3
        )
        self.assertEqual("https://req.dothttp.dev/post", third_target.url)
        self.assertEqual(b'{"hi": "hi2"}', third_target.body)

        # target first one with index
        first_target_with_name = self.get_request(
            file=f"{base_dir}/target_with_names_for_few.http", target=1
        )
        self.assertEqual("https://req.dothttp.dev/get", first_target_with_name.url)

        # target second one with index
        second_target_with_name = self.get_request(
            file=f"{base_dir}/target_with_names_for_few.http", target=2
        )
        self.assertEqual("https://req.dothttp.dev/post", second_target_with_name.url)

        # target fourth one with index

        fourone = self.get_request(
            file=f"{base_dir}/target_with_names_for_few.http", target=4
        )
        self.assertEqual("https://req.dothttp.dev/post?hi=bye", fourone.url)

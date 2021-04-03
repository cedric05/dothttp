import json
import os
import sys
import unittest

from dotextensions.server import Command
from dotextensions.server.commands import ImportPostmanCollection
from test import TestBase

dir_path = os.path.dirname(os.path.realpath(__file__))
fixtures_dir = f"{dir_path}/fixtures"


@unittest.skipUnless(sys.platform.startswith("windows"), "tests are written using windows")
class FileExecute(TestBase):
    def setUp(self) -> None:
        self.execute_handler = ImportPostmanCollection()

    def compoare(self,
                 link,
                 fileToCompare):
        response = self.execute_handler.run(Command(
            method=ImportPostmanCollection.name,
            params={
                "link": link,
            },
            id=1)
        )
        with open(os.path.join(fixtures_dir, fileToCompare), 'r') as f:
            self.assertEqual(json.load(f), response.result)

    def test_base(self):
        self.compoare(
            link="https://raw.githubusercontent.com/postmanlabs/newman/v5.2.2/test/integration/dynamic-var-replacement.postman_collection.json",
            fileToCompare="fixtures.json")

    def test_more(self):
        links = [
            "https://raw.githubusercontent.com/postmanlabs/newman/v5.2.2/test/integration/case-insen-header-sandbox.postman_collection.json",
            "https://raw.githubusercontent.com/postmanlabs/newman/v5.2.2/test/integration/clear-vars-sandbox.postman_collection.json",
            "https://raw.githubusercontent.com/postmanlabs/newman/v5.2.2/test/integration/cookie-jar.postman_collection.json",
            "https://raw.githubusercontent.com/postmanlabs/newman/v5.2.2/test/integration/crypto-md5.postman_collection.json",
            "https://raw.githubusercontent.com/postmanlabs/newman/v5.2.2/test/integration/distinct-random-int.postman_collection.json",
            "https://raw.githubusercontent.com/postmanlabs/newman/v5.2.2/test/integration/dynamic-var-replacement.postman_collection.json",
            "https://raw.githubusercontent.com/postmanlabs/newman/v5.2.2/test/integration/echo-v2.postman_collection.json",
            "https://raw.githubusercontent.com/postmanlabs/newman/v5.2.2/test/integration/hawk-auth-test.postman_collection.json",
            "https://raw.githubusercontent.com/postmanlabs/newman/v5.2.2/test/integration/head-requests.postman_collection.json",
            "https://raw.githubusercontent.com/postmanlabs/newman/v5.2.2/test/integration/helper.postman_collection.json",
            "https://raw.githubusercontent.com/postmanlabs/newman/v5.2.2/test/integration/multi-level-folders-v1.postman_collection.json",
            "https://raw.githubusercontent.com/postmanlabs/newman/v5.2.2/test/integration/multi-level-folders-v2.postman_collection.json",
            "https://raw.githubusercontent.com/postmanlabs/newman/v5.2.2/test/integration/multi-value-data.postman_collection.json",
            "https://raw.githubusercontent.com/postmanlabs/newman/v5.2.2/test/integration/multiple-form-values.postman_collection.json",
            "https://raw.githubusercontent.com/postmanlabs/newman/v5.2.2/test/integration/newman-gzip-test.postman_collection.json",
            "https://raw.githubusercontent.com/postmanlabs/newman/v5.2.2/test/integration/oauth1-var-in-url-params.postman_collection.json",
            "https://raw.githubusercontent.com/postmanlabs/newman/v5.2.2/test/integration/protocol-profile-behavior.postman_collection.json",
            "https://raw.githubusercontent.com/postmanlabs/newman/v5.2.2/test/integration/prototype-check.postman_collection.json",
            "https://raw.githubusercontent.com/postmanlabs/newman/v5.2.2/test/integration/request-body-with-get.postman_collection.json",
            "https://raw.githubusercontent.com/postmanlabs/newman/v5.2.2/test/integration/request-chaining-test.postman_collection.json",
            "https://raw.githubusercontent.com/postmanlabs/newman/v5.2.2/test/integration/request-name-in-script.postman_collection.json",
            "https://raw.githubusercontent.com/postmanlabs/newman/v5.2.2/test/integration/sandbox-libraries.postman_collection.json",
            "https://raw.githubusercontent.com/postmanlabs/newman/v5.2.2/test/integration/semicolon-tests.postman_collection.json",
            "https://raw.githubusercontent.com/postmanlabs/newman/v5.2.2/test/integration/set-next-request.postman_collection.json",
            "https://raw.githubusercontent.com/postmanlabs/newman/v5.2.2/test/integration/super-sandbox-test.postman_collection.json",
            "https://raw.githubusercontent.com/postmanlabs/newman/v5.2.2/test/integration/var-replacement.postman_collection.json",
            "https://raw.githubusercontent.com/postmanlabs/newman/v5.2.2/test/integration/whatwg-url.postman_collection.json"]
        for link in links:
            self.compoare(link, os.path.join(fixtures_dir, os.path.basename(link)))

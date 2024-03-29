import json
import os
import sys
from test import TestBase

from dotextensions.server.handlers.postman2http import ImportPostmanCollection
from dotextensions.server.models import Command
from dothttp.models.parse_models import HttpFileType

dir_path = os.path.dirname(os.path.realpath(__file__))
postman_dir = f"{dir_path}/postman"
fixtures_dir = f"{dir_path}/fixtures"


class FileExecute(TestBase):
    def setUp(self) -> None:
        self.maxDiff = 10000
        self.execute_handler = ImportPostmanCollection()

    def compare(self, link, file_to_compare, filetype=HttpFileType.Httpfile.file_type):
        print(f"running for ${link} comparing with file ${file_to_compare}")
        response = self.execute_handler.run(
            Command(
                method=ImportPostmanCollection.name,
                params={"link": link, "filetype": filetype},
                id=1,
            )
        )
        # -------------------------------------------------------------------------------------
        # # For Linux
        # with open(os.path.join(fixtures_dir, file_to_compare), 'w') as f:
        #     result_normalize = {}
        #     if 'files' in response.result:
        #         for file in response.result["files"]:
        #             result_normalize[file.replace('/', "\\")] = response.result["files"][file]
        #         json.dump({"files": result_normalize}, f)
        #     else:
        #         json.dump(response.result, f)
        # # -------------------------------------------------------------------
        # For Windows
        # with open(os.path.join(fixtures_dir, file_to_compare), 'w') as f:
        #     json.dump(response.result, f)
        # -------------------------------------------------------------------------------------
        with open(os.path.join(fixtures_dir, file_to_compare), "r") as f:
            if sys.platform.startswith("windows"):
                self.assertEqual(json.load(f), response.result)
            else:
                if "error" in response.result:
                    return self.assertEqual(json.load(f), response.result)
                result_normalize = {}
                for file in response.result["files"]:
                    result_normalize[file.replace("/", "\\")] = response.result[
                        "files"
                    ][file]
                self.assertEqual(json.load(f), {"files": result_normalize})

    def test_base(self):
        self.compare(
            link="https://raw.githubusercontent.com/postmanlabs/newman/v5.2.2/test/integration/dynamic-var-replacement.postman_collection.json",
            file_to_compare="fixtures.json",
        )

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
            "https://raw.githubusercontent.com/postmanlabs/newman/v5.2.2/test/integration/whatwg-url.postman_collection.json",
            f"{postman_dir}/apikeyauth.json",
            f"{postman_dir}/apikeyauth.2.1.json",
            f"{postman_dir}/bearer.json",
            f"{postman_dir}/bearer2.1.json",
            f"{postman_dir}/aws.2.0.json",
            f"{postman_dir}/aws.2.1.json",
            f"{postman_dir}/InheritAuth.postman_collection.json",
            f"{postman_dir}/InheritAuth.postman_collection_2_0.json",
            f"{postman_dir}/variables.postman_collection.json",
            f"{postman_dir}/descriptionobject.postman_collection.json",
            f"{postman_dir}/ntlm.postman_collection.json",
            f"{postman_dir}/multipart.postmancollection.json",
            f"{postman_dir}/dottedhost.postman_collection.json",
        ]
        for link in links:
            self.compare(link, os.path.join(fixtures_dir, os.path.basename(link)))
        #

    def test_notebook(self):
        # test httpbook
        collection = "https://raw.githubusercontent.com/postmanlabs/newman/v5.2.2/test/integration/multi-level-folders-v2.postman_collection.json"
        self.compare(
            collection,
            os.path.join(
                fixtures_dir, "multi-level-folders-v2.postman_collection.httpbook.json"
            ),
            filetype=HttpFileType.Notebookfile.file_type,
        )

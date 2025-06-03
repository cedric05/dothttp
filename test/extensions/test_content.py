import json
from test import TestBase
from typing import Union

from dotextensions.server.handlers.basic_handlers import ContentExecuteHandler
from dotextensions.server.models import Command


class FileExecute(TestBase):
    def setUp(self) -> None:
        self.execute_handler = ContentExecuteHandler()

    def test_execute_content(self):
        result = self.execute_and_result("GET http://localhost:8000/get")
        self.compare_results(result, "http://localhost:8000/get")

    def compare_results(self, result, url):
        body = json.loads(result.result["body"])
        self.assertTrue("args" in body)
        self.assertTrue("headers" in body)
        self.assertEqual({}, body["args"])
        self.assertEqual(url, body["url"])
        self.assertEqual(200, result.result["status"])

    def test_405_execute_content(self):
        result = self.execute_and_result("GET http://localhost:8000/post")
        self.assertEqual(405, result.result["status"])

    def execute_and_result(
        self, content, target: Union[str, int] = 1, contexts=None, curl=False
    ):
        return self.execute_handler.run(
            Command(
                method=ContentExecuteHandler.name,
                params={
                    "content": content,
                    "properties": {"post": "get"},
                    "target": target,
                    "contexts": contexts,
                    "curl": curl,
                },
                id=1,
            )
        )
        
    def get_context_request_comp(
        self, content, target: Union[str, int] = 1, contexts=None, curl=False
    ):
        command = Command(
                method=ContentExecuteHandler.name,
                params={
                    "content": content,
                    "properties": {"post": "get"},
                    "target": target,
                    "contexts": contexts,
                    "curl": curl,
                },
                id=1,
            )
        executor = ContentExecuteHandler()
        config = executor.get_config(command)
        request_comp = executor.get_request_comp(config)
        return request_comp

    def test_fail_syntax(self):
        result = self.execute_and_result("GET2 http://localhost:8000/post")
        self.assertEqual(True, result.result["error"])

    def test_properties(self):
        """env doesnt live as it has no relative .dothttp.json path"""
        result = self.execute_and_result("GET http://localhost:8000/{{post}}")
        self.compare_results(result, "http://localhost:8000/get")

    def test_execute_content_context(self):
        # tests to confirm contexts can be used
        # (curl and run)
        kwargs = dict(
            content="""
            @name('test'):"base"
            POST ""
            json({
                "hai":"{{testvar}}"
            })
            """,
            target="test",
            contexts=[
                # invalid context
                "",
                # valid content
                """
                @name("base")
                // {{testvar=bye}}
                POST http://localhost:8000/post
                """,
            ],
        )
        self.assertEqual(
            """curl -X POST --url http://localhost:8000/post \\
-H \'content-type: application/json\' \\
-d \'{
    "hai": "bye"
}\'""",
            self.execute_and_result(curl=True, **kwargs).result["body"],
        )

        self.assertEqual(
            200, self.execute_and_result(curl=False, **kwargs).result["status"]
        )

    def test_execute_content_context_error(self):
        # tests to throw when base is not found
        result = self.execute_and_result(
            """
            @name('test'):"base"
            POST "https://google.com"
            """,
            target="test",
            contexts=["", ""],
            curl=True,
        )
        self.assertTrue(result.result["error"])
        self.assertEqual(
            "http def with name `base` not defined for http  with name `test`",
            result.result["error_message"],
        )

    def test_execute_content_context_multiple_base(self):
        # tests to pick first context if multiple contexts are there
        result = self.execute_and_result(
            """
            @name('test'):"base"
            POST ""
            """,
            target="test",
            contexts=[
                # as it is not single file
                # there can be multiple targets
                # defined with same name
                # in such scenario
                # only first one will be picked
                """
                @name('base')
                POST "https://req.dothttp.dev/ram"
                """,
                """
                @name('base')
                POST "https://req.dothttp.dev/krishna"
                """,
            ],
            curl=True,
        )
        # picks first one out multiple similar bases
        # same behaviour will not be observed in case of http file
        # in http file, it will throw error mentioning duplicate target found
        self.assertEqual(
            """curl -X POST --url https://req.dothttp.dev/ram \\
""",
            result.result["body"],
        )

    def test_execute_content_context_with_var_normal(self):
        # tests to pick first context if multiple contexts are there
        result = self.execute_and_result(
            """
            @name('test')
            POST "http://localhost:8000/post"
            json({
                "a":{{a}},
                "b":"{{b}}",
            })

            """,
            target="test",
            contexts=[
                # as it is not single file
                # there can be multiple targets
                # defined with same name
                # in such scenario
                # only first one will be picked
                """
                var a = 10;
                """,
                """
                var b = 20;
                """
            ],
            curl=False,
        )
        self.assertEqual(
            {
                "a": 10,
                "b": '20',
            },
            json.loads(result.result["body"])["json"],
        )


    def test_execute_content_context_with_var_with_json(self):
        # tests to pick first context if multiple contexts are there
        result = self.execute_and_result(
            """
            @name('test')
            POST "http://localhost:8000/post"
            json({
                "c" : {{c}}
            })

            """,
            target="test",
            contexts=[
                """
                var c = {"ram":"ranga", "raja":[1, true, false, null]};
                """
            ],
            curl=False,
        )
        self.assertEqual(
            {
                "c" : {"ram":"ranga", "raja":[1, True, False, None]}
            },
            json.loads(result.result["body"])["json"],
        )
        
    def test_var_override(self):
        # tests to pick first context if multiple contexts are there
        result = self.get_context_request_comp(
            """
            var a = 10;
            @name('test')
            POST "http://localhost:8000/post"
            json({
                "a" : {{a}}
            })

            """,
            target="test",
            contexts=[
                """
                var a = 12;
                """
            ],
            curl=False,
        )
        result.load_def()
        self.assertEquals(result.httpdef.payload.json["a"], 10)
        
        
    def test_from_context_with_var(self):
        # tests to pick first context if multiple contexts are there
        result = self.get_context_request_comp(
            """
            @name('test')
            POST "http://localhost:8000/post"
            json({
                "a" : {{a}}
            })

            """,
            target="test",
            contexts=[
                """
                var a = 12;
                """
            ],
            curl=False,
        )
        result.load_def()
        self.assertEquals(result.httpdef.payload.json["a"], 12)
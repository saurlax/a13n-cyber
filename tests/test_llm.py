import io
import json
import os
import unittest
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import replace
from unittest.mock import patch

import httpx2
from openai import APIStatusError, APITimeoutError, DefaultAsyncHttpx2Client

from tsec_agent.cli import main
from tsec_agent.config import Config
from tsec_agent.llm import smoke


class SmokeTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.requests = []
        self.clients = []
        self.config = Config(
            base_url="https://model.test/v1",
            model="test-chat-model",
            api_key="offline-test-key",
            timeout=17,
            max_output_tokens=23,
        )
        self.response = httpx2.Response(
            200,
            json={
                "id": "offline",
                "object": "chat.completion",
                "created": 0,
                "model": "test-chat-model",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "private-fixture"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 5,
                    "completion_tokens": 2,
                    "total_tokens": 7,
                },
            },
        )

        def transport(request):
            self.requests.append(request)
            if isinstance(self.response, Exception):
                raise self.response
            return self.response

        def client_factory(**kwargs):
            client = DefaultAsyncHttpx2Client(
                transport=httpx2.MockTransport(transport), **kwargs
            )
            self.clients.append(client)
            return client

        replacement = patch("tsec_agent.llm.DefaultAsyncHttpx2Client", client_factory)
        replacement.start()
        self.addCleanup(replacement.stop)

    async def test_single_bounded_request_returns_only_metadata(self):
        result = await smoke(self.config)
        self.assertEqual(len(self.requests), 1)
        request = self.requests[0]
        self.assertEqual(str(request.url), "https://model.test/v1/chat/completions")
        body = json.loads(request.content)
        self.assertEqual(body["model"], self.config.model)
        self.assertEqual(body["max_tokens"], 23)
        self.assertFalse(body["stream"])
        self.assertNotIn("reasoning_effort", body)
        self.assertEqual(request.extensions["timeout"]["read"], 17)
        self.assertEqual(
            result,
            {
                "status": "ok",
                "response_has_text": True,
                "usage": {
                    "prompt_tokens": 5,
                    "completion_tokens": 2,
                    "total_tokens": 7,
                },
            },
        )
        self.assertNotIn("private-fixture", json.dumps(result))
        self.assertTrue(self.clients[0].is_closed)

    async def test_explicit_reasoning_effort_is_forwarded(self):
        await smoke(replace(self.config, reasoning_effort="high"))
        self.assertEqual(
            json.loads(self.requests[0].content)["reasoning_effort"], "high"
        )

    async def test_errors_are_not_retried_and_close_the_client(self):
        for code in (429, 500):
            with self.subTest(code=code):
                self.requests.clear()
                self.response = httpx2.Response(code, json={"error": "offline failure"})
                with self.assertRaises(APIStatusError):
                    await smoke(self.config)
                self.assertEqual(len(self.requests), 1)
                self.assertTrue(self.clients[-1].is_closed)

    async def test_redirect_is_not_followed(self):
        self.response = httpx2.Response(
            302, headers={"location": "https://redirect.test/v1/chat/completions"}
        )
        with self.assertRaises(APIStatusError):
            await smoke(self.config)
        self.assertEqual(len(self.requests), 1)
        self.assertTrue(self.clients[0].is_closed)

    async def test_timeout_is_not_retried(self):
        self.response = httpx2.ReadTimeout("offline timeout")
        with self.assertRaises(APITimeoutError):
            await smoke(self.config)
        self.assertEqual(len(self.requests), 1)
        self.assertTrue(self.clients[0].is_closed)

    async def test_empty_completion_is_rejected(self):
        self.response = httpx2.Response(200, json={"choices": []})
        with self.assertRaisesRegex(RuntimeError, "no valid completion"):
            await smoke(self.config)


class SmokeCliTests(unittest.TestCase):
    def test_provider_error_body_is_not_printed(self):
        requests = []

        def transport(request):
            requests.append(request)
            return httpx2.Response(500, json={"error": {"message": "private-fixture"}})

        def client_factory(**kwargs):
            return DefaultAsyncHttpx2Client(
                transport=httpx2.MockTransport(transport), **kwargs
            )

        output, errors = io.StringIO(), io.StringIO()
        with (
            patch.dict(
                os.environ,
                {
                    "LLM_BASE_URL": "https://model.test/v1",
                    "LLM_MODEL": "test-chat-model",
                    "LLM_API_KEY": "offline-test-key",
                },
                clear=True,
            ),
            patch("tsec_agent.llm.DefaultAsyncHttpx2Client", client_factory),
            redirect_stdout(output),
            redirect_stderr(errors),
        ):
            self.assertEqual(main(["llm-smoke"]), 1)
        self.assertEqual(len(requests), 1)
        self.assertEqual(output.getvalue(), "")
        self.assertEqual(json.loads(errors.getvalue())["reason"], "InternalServerError")
        self.assertNotIn("private-fixture", errors.getvalue())
        self.assertNotIn("offline-test-key", errors.getvalue())

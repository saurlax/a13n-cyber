import asyncio
import json
import signal
import unittest
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

import httpx2
from openai import AsyncOpenAI

from tsec_agent.application import Interrupted, execute, run_application
from tsec_agent.cli import parser
from tsec_agent.config import Config


class ApplicationTests(unittest.IsolatedAsyncioTestCase):
    async def test_general_command_uses_chat_completions_transport(self):
        requests = []

        def transport(request):
            body = json.loads(request.content)
            requests.append(body)
            self.assertEqual(request.url.path, "/v1/chat/completions")
            self.assertEqual(body["model"], "test-chat-model")
            self.assertTrue(body["stream"])
            chunk = {
                "id": "offline",
                "object": "chat.completion.chunk",
                "created": 0,
                "model": "test-chat-model",
                "choices": [
                    {
                        "index": 0,
                        "delta": {"role": "assistant", "content": "Transport verified"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 2,
                    "total_tokens": 12,
                },
            }
            return httpx2.Response(
                200,
                headers={"content-type": "text/event-stream"},
                content="data: " + json.dumps(chunk) + "\n\ndata: [DONE]\n\n",
            )

        def client_factory(**kwargs):
            return AsyncOpenAI(
                **kwargs,
                http_client=httpx2.AsyncClient(
                    transport=httpx2.MockTransport(transport)
                ),
            )

        with TemporaryDirectory() as directory:
            args = parser().parse_args(
                ["run", "Check transport", "--workspace", directory]
            )
            config = Config(
                base_url="https://model.test/v1",
                model="test-chat-model",
                api_key="test-model-key",
            )
            with patch("tsec_agent.application.AsyncOpenAI", client_factory):
                result = await execute(args, config)
        self.assertEqual(result["output"], "Transport verified")
        self.assertEqual(result["usage"]["requests"], 1)
        self.assertEqual(len(requests), 1)

    async def test_deadline_waits_for_cleanup(self):
        cleaned = []

        async def execute(args, config):
            try:
                await asyncio.Event().wait()
            finally:
                await asyncio.sleep(0)
                cleaned.append(True)

        with patch("tsec_agent.application.execute", execute):
            with self.assertRaises(TimeoutError):
                await run_application(
                    SimpleNamespace(timeout=0.01),
                    Config(
                        base_url="https://model.test/v1",
                        model="test-chat-model",
                        api_key="test-key",
                    ),
                )
        self.assertEqual(cleaned, [True])

    async def test_sigterm_cancels_then_restores_handler(self):
        cleaned = []
        previous = signal.getsignal(signal.SIGTERM)

        async def execute(args, config):
            try:
                signal.raise_signal(signal.SIGTERM)
                await asyncio.Event().wait()
            finally:
                await asyncio.sleep(0)
                cleaned.append(True)

        with patch("tsec_agent.application.execute", execute):
            with self.assertRaises(Interrupted) as exc:
                await run_application(
                    SimpleNamespace(timeout=10),
                    Config(
                        base_url="https://model.test/v1",
                        model="test-chat-model",
                        api_key="test-key",
                    ),
                )
        self.assertEqual(exc.exception.exit_code, 143)
        self.assertEqual(cleaned, [True])
        self.assertEqual(signal.getsignal(signal.SIGTERM), previous)

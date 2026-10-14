"""Offline integration of real Harness and SDK clients over a mock transport."""

import json
import unittest
from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory

import httpx
from pydantic_ai.messages import ToolReturnPart
from pydantic_ai.models.function import DeltaToolCall, FunctionModel
from test_benchmark import challenge
from tsec_benchmark import TSecBenchmarkAsync

from tsec_agent.benchmark import BenchmarkRunner
from tsec_agent.runtime import Budget, CyberAgent


class IntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_sdk_and_harness_complete_a_challenge(self):
        state = asdict(challenge())
        events = []

        async def transport(request):
            if request.url.host == "10.0.100.58":
                return httpx.Response(200, json={"status": "ok"})
            self.assertEqual(request.headers["BENCHMARK_TOKEN"], "test-task-token")
            events.append((request.method, request.url.path))
            if request.url.path.endswith("/start"):
                return httpx.Response(
                    200,
                    json={"unique_code": "first", "container_addr": ["127.0.0.1:8080"]},
                )
            if request.url.path.endswith("/submit"):
                self.assertEqual(
                    json.loads(request.content),
                    {"unique_code": "first", "flag": "candidate"},
                )
                state.update(is_completed=True, correct_flag_count=1)
                return httpx.Response(
                    200,
                    json={
                        "correct": True,
                        "awarded": 100,
                        "cumulative_score": 100,
                        "correct_flag_count": 1,
                        "total_flag_count": 1,
                        "matched_flag_index": 0,
                    },
                )
            if request.url.path.endswith("/close"):
                return httpx.Response(
                    200, json={"unique_code": "first", "closed": True}
                )
            return httpx.Response(200, json=[state])

        async def respond(messages, info):
            self.assertNotIn("test-task-token", str(messages))
            if any(isinstance(p, ToolReturnPart) for m in messages for p in m.parts):
                yield "Confirmed by the platform"
            else:
                yield {
                    0: DeltaToolCall(
                        name="submit_flag", json_args='{"flag":"candidate"}'
                    )
                }

        with TemporaryDirectory() as root:
            agent = CyberAgent(
                FunctionModel(stream_function=respond), project=Path(root)
            )
            async with TSecBenchmarkAsync(
                base_url="https://benchmark.test",
                token="test-task-token",
                transport=httpx.MockTransport(transport),
            ) as client:
                result = await BenchmarkRunner(
                    client, agent, Path(root), Budget()
                ).run()
        self.assertEqual(result["stop_reason"], "all_completed")
        self.assertIn(("POST", "/openapi/v1/challenges/submit"), events)
        self.assertIn(("POST", "/openapi/v1/challenges/close"), events)
        self.assertNotIn("test-task-token", json.dumps(result))

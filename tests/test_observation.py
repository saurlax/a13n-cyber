import io
import json
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from pydantic_ai.messages import (
    FunctionToolCallEvent,
    FunctionToolResultEvent,
    PartDeltaEvent,
    PartStartEvent,
    TextPart,
    TextPartDelta,
    ToolCallPart,
    ToolReturnPart,
)
from pydantic_ai.models.function import DeltaToolCall, FunctionModel

from tsec_agent.observation import EventTrace
from tsec_agent.runtime import AgentExecutionError, Budget, CyberAgent


class ObservationTests(unittest.TestCase):
    def test_streamed_secrets_and_tool_credentials_are_redacted(self):
        usage = SimpleNamespace(
            requests=1, input_tokens=10, output_tokens=5, total_tokens=15
        )
        console = io.StringIO()
        events = [
            PartStartEvent(index=0, part=TextPart("Before model-")),
            PartDeltaEvent(index=0, delta=TextPartDelta("credential after")),
            FunctionToolCallEvent(
                ToolCallPart("submit_flag", {"flag": "private-flag"})
            ),
            FunctionToolResultEvent(
                ToolReturnPart(
                    "probe", {"api_key": "hidden-value", "output": "benchmark-secret"}
                )
            ),
        ]
        with TemporaryDirectory() as directory:
            with (
                redirect_stderr(console),
                EventTrace(
                    directory,
                    console=True,
                    secrets=("model-credential", "benchmark-secret"),
                ) as trace,
            ):
                for index, event in enumerate(events):
                    trace.observe(
                        SimpleNamespace(event=event, run_id="test", sequence=index),
                        usage,
                    )
                content = (Path(directory) / "agent.jsonl").read_text(encoding="utf-8")
                records = [json.loads(line) for line in content.splitlines()]
                self.assertEqual(len(records), 4)
                self.assertNotEqual(content, console.getvalue())
                for secret in (
                    "model-credential",
                    "benchmark-secret",
                    "hidden-value",
                    "private-flag",
                ):
                    self.assertNotIn(secret, console.getvalue())
                self.assertIn("[Agent]", console.getvalue())
                self.assertIn("[Tool: submit_flag]", console.getvalue())
                self.assertNotIn("model-credential", content)
                self.assertNotIn("benchmark-secret", content)
                self.assertNotIn("hidden-value", content)
                self.assertNotIn("private-flag", content)
                self.assertNotIn("model-", content)
                progress = json.loads((Path(directory) / "progress.json").read_text())
                self.assertNotIn("data", progress)
                self.assertEqual(progress["usage"]["total_tokens"], 15)

    def test_interrupted_secret_prefix_is_not_flushed(self):
        console = io.StringIO()
        with (
            redirect_stderr(console),
            EventTrace(console=True, secrets=("secret-value",)) as trace,
        ):
            self.assertEqual(trace.fragment(("run", 0), "normal secret-"), "normal ")
        self.assertNotIn("secret-", console.getvalue())


class NativeObservationTests(unittest.IsolatedAsyncioTestCase):
    async def test_failed_run_preserves_failure_code_and_usage(self):
        async def probe() -> str:
            """Return a harmless observation."""
            return "Continue"

        async def respond(messages, info):
            yield {0: DeltaToolCall(name="probe", json_args="{}")}

        with TemporaryDirectory() as directory:
            root = Path(directory)
            with EventTrace(root / "logs") as trace:
                agent = CyberAgent(
                    FunctionModel(stream_function=respond), project=root, observer=trace
                )
                with self.assertRaises(AgentExecutionError):
                    await agent.run(
                        "Offline budget check", root, Budget(request_limit=1), (probe,)
                    )
            progress = json.loads((root / "logs" / "progress.json").read_text())
            self.assertEqual(progress["run_status"], "failed")
            self.assertTrue(progress["failure_code"])
            self.assertEqual(progress["usage"]["requests"], 1)

    async def test_native_harness_stream_is_persisted_without_changing_execution(self):
        async def probe() -> dict:
            """Return a harmless runtime observation."""
            return {"stdout": "tool-output-fixture"}

        async def respond(messages, info):
            results = [
                p for m in messages for p in m.parts if isinstance(p, ToolReturnPart)
            ]
            if results:
                yield "runtime-"
                yield "complete"
            else:
                yield {0: DeltaToolCall(name="probe", json_args="{}")}

        with TemporaryDirectory() as directory:
            root = Path(directory)
            with EventTrace(root / "logs") as trace:
                agent = CyberAgent(
                    FunctionModel(stream_function=respond), project=root, observer=trace
                )
                output = await agent.run(
                    "Run an offline check", root, Budget(), (probe,)
                )
            self.assertEqual(output, "runtime-complete")
            records = [
                json.loads(line)
                for line in (root / "logs" / "agent.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            ]
            self.assertTrue(any(r["event"] == "function_tool_call" for r in records))
            self.assertTrue(
                any(
                    r["data"].get("result") == {"stdout": "tool-output-fixture"}
                    for r in records
                )
            )
            self.assertEqual(records[-1]["event"], "run_result")
            self.assertEqual(records[-1]["data"]["status"], "completed")
            self.assertEqual(records[-1]["usage"]["requests"], 2)
            progress = json.loads((root / "logs" / "progress.json").read_text())
            self.assertEqual(progress["run_status"], "completed")
            self.assertNotIn("tool-output-fixture", json.dumps(progress))

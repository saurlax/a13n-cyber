import io
import json
import os
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from tsec_agent.cli import main
from tsec_agent.console import ConsoleRenderer, view_logs


class ConsoleTests(unittest.TestCase):
    def test_fragments_are_joined_and_tool_output_preserves_newlines(self):
        output = io.StringIO()
        renderer = ConsoleRenderer(output)
        records = [
            {
                "event": "part_start",
                "data": {"channel": "text", "index": 0, "text": "Hello "},
            },
            {
                "event": "part_delta",
                "data": {"channel": "text", "index": 0, "text": "world"},
            },
            {
                "event": "function_tool_call",
                "data": {"tool": "probe", "arguments": {"command": "echo ok"}},
            },
            {
                "event": "function_tool_result",
                "data": {
                    "tool": "probe",
                    "result": {"stdout": "first\nsecond", "exit_code": 0},
                },
            },
            {
                "event": "run_result",
                "data": {"status": "completed"},
                "usage": {"requests": 2, "total_tokens": 12345},
            },
        ]
        for record in records:
            renderer.render(record)
        text = output.getvalue()
        self.assertIn("Hello world", text)
        self.assertEqual(text.count("[Agent]"), 1)
        self.assertIn("[Tool: probe]", text)
        self.assertIn("first\n  second", text)
        self.assertIn("Tokens: 12,345", text)
        self.assertNotIn('"event":', text)

    def test_logs_command_is_offline_and_needs_no_model_credentials(self):
        with TemporaryDirectory() as directory:
            source = Path(directory) / "agent.jsonl"
            source.write_text(
                json.dumps({"event": "part_start", "data": {"text": "offline fixture"}})
                + "\n",
                encoding="utf-8",
            )
            output = io.StringIO()
            with patch.dict(os.environ, {}, clear=True), redirect_stdout(output):
                self.assertEqual(main(["logs", directory]), 0)
            self.assertIn("offline fixture", output.getvalue())

    def test_follow_waits_for_a_complete_appended_record(self):
        record = json.dumps(
            {"event": "part_start", "data": {"text": "complete fixture"}}
        )
        with TemporaryDirectory() as directory:
            source = Path(directory) / "agent.jsonl"
            source.write_text(record[:20], encoding="utf-8")
            sleeps = 0

            def append_or_stop(_):
                nonlocal sleeps
                sleeps += 1
                if sleeps == 1:
                    with source.open("a", encoding="utf-8") as writer:
                        writer.write(record[20:] + "\n")
                else:
                    raise KeyboardInterrupt

            output = io.StringIO()
            with (
                redirect_stdout(output),
                patch("tsec_agent.console.time.sleep", append_or_stop),
                self.assertRaises(KeyboardInterrupt),
            ):
                view_logs(source, follow=True)
            self.assertEqual(output.getvalue().count("complete fixture"), 1)

import io
import json
import os
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

from tsec_agent.cli import main, parser


class CliTests(unittest.TestCase):
    def test_bare_command_is_help(self):
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(main([]), 0)
        self.assertIn("tsecbench", output.getvalue())

    def test_nonpositive_limits_are_argument_errors(self):
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as exc:
            parser().parse_args(["run", "task", "--request-limit", "0"])
        self.assertEqual(exc.exception.code, 2)

    def test_empty_task_is_argument_error(self):
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as exc:
            main(["run", " "])
        self.assertEqual(exc.exception.code, 2)

    def test_doctor_is_offline_and_redacts_secrets(self):
        output = io.StringIO()
        with (
            patch.dict(os.environ, {"LLM_API_KEY": "test-secret"}, clear=True),
            redirect_stdout(output),
        ):
            self.assertEqual(main(["doctor"]), 0)
        self.assertEqual(json.loads(output.getvalue())["network_requests"], 0)
        self.assertNotIn("test-secret", output.getvalue())

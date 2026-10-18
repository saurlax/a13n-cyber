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

    def test_challenge_count_limit_is_rejected(self):
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as exc:
            parser().parse_args(["tsecbench", "--max-challenges", "1"])
        self.assertEqual(exc.exception.code, 2)

    def test_execution_defaults_allow_full_evaluation(self):
        for command in (["run", "task"], ["tsecbench"]):
            with self.subTest(command=command):
                args = parser().parse_args(command)
                self.assertEqual(args.request_limit, 10_000)
                self.assertEqual(args.token_limit, 100_000_000)
                self.assertEqual(args.timeout, 21_600)
        self.assertEqual(parser().parse_args(["tsecbench"]).challenge_timeout, 3600)

    def test_empty_task_is_argument_error(self):
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as exc:
            main(["run", " "])
        self.assertEqual(exc.exception.code, 2)

    def test_doctor_is_offline_and_redacts_secrets(self):
        output = io.StringIO()
        with (
            patch.dict(
                os.environ,
                {
                    "LLM_BASE_URL": "https://model.test/v1",
                    "LLM_MODEL": "test-chat-model",
                    "LLM_API_KEY": "test-secret",
                },
                clear=True,
            ),
            redirect_stdout(output),
        ):
            self.assertEqual(main(["doctor"]), 0)
        self.assertEqual(json.loads(output.getvalue())["network_requests"], 0)
        self.assertNotIn("test-secret", output.getvalue())

    def test_missing_model_configuration_fails_before_execution(self):
        for command in (["doctor"], ["llm-smoke"], ["run", "task"], ["tsecbench"]):
            with self.subTest(command=command):
                errors = io.StringIO()
                with (
                    patch.dict(os.environ, {}, clear=True),
                    redirect_stderr(errors),
                    patch("tsec_agent.cli.smoke") as smoke,
                ):
                    self.assertEqual(main(command), 1)
                smoke.assert_not_called()
                self.assertIn("LLM_BASE_URL", errors.getvalue())
                self.assertIn("LLM_MODEL", errors.getvalue())
                self.assertIn("LLM_API_KEY", errors.getvalue())

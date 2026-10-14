import json
import os
import unittest
from unittest.mock import patch

from tsec_agent.config import Config


class ConfigTests(unittest.TestCase):
    def test_secrets_not_in_repr_or_summary(self):
        with patch.dict(
            os.environ,
            {
                "STEPFUN_API_KEY": "secret-model-key",
                "BENCHMARK_TOKEN": "secret-bench-key",
            },
            clear=True,
        ):
            config = Config.from_env()
        output = repr(config) + json.dumps(config.public_summary())
        self.assertNotIn("secret-model-key", output)
        self.assertNotIn("secret-bench-key", output)

    def test_rejects_credentials_in_endpoint(self):
        with patch.dict(
            os.environ,
            {"LLM_BASE_URL": "https://user:secret@example.com/v1"},
            clear=True,
        ):
            with self.assertRaises(ValueError):
                Config.from_env()

    def test_rejects_empty_hosted_endpoint(self):
        with patch.dict(os.environ, {"LLM_BASE_URL": ""}, clear=True):
            with self.assertRaises(ValueError):
                Config.from_env()

    def test_defaults_use_official_model_id(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(Config.from_env().model, "step-5-preview")


if __name__ == "__main__":
    unittest.main()

import json
import os
import unittest
from unittest.mock import patch

from tsec_agent.config import Config, ConfigurationError

MODEL_ENV = {
    "LLM_BASE_URL": "https://model.test/v1",
    "LLM_MODEL": "test-chat-model",
    "LLM_API_KEY": "secret-model-key",
}


class ConfigTests(unittest.TestCase):
    def test_secrets_not_in_repr_or_summary(self):
        with patch.dict(
            os.environ, {**MODEL_ENV, "BENCHMARK_TOKEN": "secret-bench-key"}, clear=True
        ):
            config = Config.from_env()
        output = repr(config) + json.dumps(config.public_summary())
        self.assertNotIn("secret-model-key", output)
        self.assertNotIn("secret-bench-key", output)

    def test_each_model_variable_is_required_without_fallback(self):
        for variable in MODEL_ENV:
            for value in (None, "", "   "):
                with self.subTest(variable=variable, value=value):
                    values = dict(MODEL_ENV)
                    if value is None:
                        del values[variable]
                    else:
                        values[variable] = value
                    with patch.dict(os.environ, values, clear=True):
                        with self.assertRaisesRegex(ConfigurationError, variable):
                            Config.from_env()

    def test_vendor_key_does_not_replace_required_api_key(self):
        values = {**MODEL_ENV, "STEPFUN_API_KEY": "legacy-secret"}
        del values["LLM_API_KEY"]
        with patch.dict(os.environ, values, clear=True):
            with self.assertRaisesRegex(ConfigurationError, "LLM_API_KEY"):
                Config.from_env()

    def test_only_explicit_generic_api_key_is_used(self):
        with patch.dict(
            os.environ, {**MODEL_ENV, "STEPFUN_API_KEY": "legacy-secret"}, clear=True
        ):
            config = Config.from_env()
        self.assertEqual(config.api_key, MODEL_ENV["LLM_API_KEY"])
        self.assertIsNone(config.reasoning_effort)

    def test_rejects_credentials_in_endpoint_without_echoing_them(self):
        values = {
            **MODEL_ENV,
            "LLM_BASE_URL": "https://user:private-value@example.com/v1",
        }
        with patch.dict(os.environ, values, clear=True):
            with self.assertRaises(ConfigurationError) as exc:
                Config.from_env()
        self.assertNotIn("private-value", str(exc.exception))

    def test_preserves_explicit_endpoint_and_model(self):
        with patch.dict(os.environ, MODEL_ENV, clear=True):
            config = Config.from_env()
        self.assertEqual(config.base_url, MODEL_ENV["LLM_BASE_URL"])
        self.assertEqual(config.model, MODEL_ENV["LLM_MODEL"])


if __name__ == "__main__":
    unittest.main()

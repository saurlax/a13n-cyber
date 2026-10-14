import os
from dataclasses import dataclass, field
from urllib.parse import urlsplit


@dataclass(frozen=True)
class Config:
    base_url: str
    model: str
    api_key: str = field(repr=False)
    benchmark_url: str = ""
    benchmark_token: str = field(default="", repr=False)
    reasoning_effort: str = "high"
    max_output_tokens: int = 512
    timeout: int = 60

    @classmethod
    def from_env(cls):
        result = cls(
            base_url=os.getenv(
                "LLM_BASE_URL", "https://api.stepfun.com/step_plan/v1"
            ).rstrip("/"),
            model=os.getenv("LLM_MODEL", "step-5-preview"),
            api_key=os.getenv("STEPFUN_API_KEY", "") or os.getenv("LLM_API_KEY", ""),
            benchmark_url=os.getenv("BENCHMARK_BASE_URL", ""),
            benchmark_token=os.getenv("BENCHMARK_TOKEN", ""),
            reasoning_effort=os.getenv("LLM_REASONING_EFFORT", "high"),
            max_output_tokens=int(os.getenv("LLM_MAX_OUTPUT_TOKENS", "512")),
            timeout=int(os.getenv("LLM_REQUEST_TIMEOUT", "60")),
        )
        result.validate()
        return result

    def validate(self):
        parsed = urlsplit(self.base_url)
        if parsed.scheme not in {"https", "http"} or not parsed.hostname:
            raise ValueError("LLM_BASE_URL must be an absolute HTTP(S) URL")
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError(
                "LLM_BASE_URL must not contain credentials, query, or fragment"
            )
        if not self.model.strip():
            raise ValueError("LLM_MODEL must not be empty")
        if self.reasoning_effort not in {"low", "medium", "high"}:
            raise ValueError("LLM_REASONING_EFFORT must be low, medium, or high")
        if not 1 <= self.max_output_tokens <= 65536:
            raise ValueError("LLM_MAX_OUTPUT_TOKENS must be between 1 and 65536")
        if not 1 <= self.timeout <= 600:
            raise ValueError("LLM_REQUEST_TIMEOUT must be between 1 and 600")

    def public_summary(self):
        return {
            "base_url": self.base_url,
            "model": self.model,
            "api_key_configured": bool(self.api_key),
            "benchmark_url_configured": bool(self.benchmark_url),
            "benchmark_token_configured": bool(self.benchmark_token),
            "reasoning_effort": self.reasoning_effort,
            "max_output_tokens": self.max_output_tokens,
            "request_timeout_seconds": self.timeout,
        }

    def require_model(self):
        if not self.api_key.strip():
            raise ValueError("Set STEPFUN_API_KEY or LLM_API_KEY")

    def require_benchmark(self):
        parsed = urlsplit(self.benchmark_url)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("BENCHMARK_BASE_URL must be a credential-free HTTP(S) URL")
        if not self.benchmark_token.strip():
            raise ValueError("Set BENCHMARK_TOKEN")

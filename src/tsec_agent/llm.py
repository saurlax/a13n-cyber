import json
import urllib.error
import urllib.request

from .config import Config


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def smoke(config: Config):
    """One bounded, benign API request; never executed by offline checks."""
    if not config.api_key:
        raise ValueError("Set STEPFUN_API_KEY or LLM_API_KEY before llm-smoke")
    payload = {
        "model": config.model,
        "messages": [{"role": "user", "content": "Reply with OK only."}],
        "max_tokens": config.max_output_tokens,
        "reasoning_effort": config.reasoning_effort,
        "stream": False,
    }
    request = urllib.request.Request(
        config.base_url + "/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": "Bearer " + config.api_key, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.build_opener(NoRedirect()).open(request, timeout=config.timeout) as response:
            result = json.load(response)
    except urllib.error.HTTPError as exc:
        # API error bodies can echo request details. Keep them out of logs.
        raise RuntimeError(f"Model request failed with HTTP {exc.code}") from None
    except (urllib.error.URLError, TimeoutError):
        raise RuntimeError("Model request failed: connection or timeout error") from None
    choices = result.get("choices", []) if isinstance(result, dict) else []
    if not choices or not isinstance(choices[0], dict) or not isinstance(choices[0].get("message"), dict):
        raise RuntimeError("Model response has no valid completion")
    # Return metadata only; no prompts, credentials, reasoning, or completion text.
    content = choices[0]["message"].get("content")
    return {"status": "ok", "response_has_text": bool(content), "usage": result.get("usage", {})}

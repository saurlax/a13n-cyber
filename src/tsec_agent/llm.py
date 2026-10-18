"""Explicit model connectivity check using the runtime's OpenAI SDK."""

from openai import AsyncOpenAI, DefaultAsyncHttpx2Client, omit

from .config import Config


async def smoke(config: Config):
    """One bounded, benign API request; never executed by offline checks."""
    config.require_model()
    async with AsyncOpenAI(
        base_url=config.base_url,
        api_key=config.api_key,
        timeout=config.timeout,
        max_retries=0,
        http_client=DefaultAsyncHttpx2Client(follow_redirects=False),
    ) as client:
        result = await client.chat.completions.create(
            model=config.model,
            messages=[{"role": "user", "content": "Reply with OK only."}],
            max_tokens=config.max_output_tokens,
            reasoning_effort=config.reasoning_effort or omit,
            stream=False,
        )
    if not result.choices:
        raise RuntimeError("Model response has no valid completion")
    # Return metadata only; the CLI reports SDK failures without their bodies.
    return {
        "status": "ok",
        "response_has_text": bool(result.choices[0].message.content),
        "usage": result.usage.model_dump(exclude_none=True) if result.usage else {},
    }

"""Application resources, cancellation, and execution mode dispatch."""

from __future__ import annotations

import asyncio
import logging
import signal
from contextlib import aclosing
from pathlib import Path

from openai import AsyncOpenAI
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from tsec_benchmark import TSecBenchmarkAsync

from .benchmark import BenchmarkRunner
from .config import Config
from .runtime import AgentConfiguration, Budget, CyberAgent

logger = logging.getLogger(__name__)


class Interrupted(RuntimeError):
    def __init__(self, signum: int):
        self.exit_code = 128 + signum
        super().__init__("Execution interrupted")


async def execute(args, config: Config) -> dict:
    config.require_model()
    if args.command == "tsecbench":
        config.require_benchmark()
    spec = (
        AgentConfiguration.from_file(args.agent_spec)
        if args.agent_spec
        else AgentConfiguration()
    )
    settings = dict(spec.model_settings or {})
    settings["openai_reasoning_effort"] = config.reasoning_effort
    spec = spec.with_updates(model_settings=settings)
    budget = Budget(args.request_limit, args.token_limit)
    project = Path(args.workspace).resolve()
    project.mkdir(parents=True, exist_ok=True)
    async with AsyncOpenAI(
        base_url=config.base_url,
        api_key=config.api_key,
        timeout=config.timeout,
        max_retries=0,
    ) as client:
        model = OpenAIChatModel(
            config.model, provider=OpenAIProvider(openai_client=client)
        )
        agent = CyberAgent(model, project=project, spec=spec)
        if args.command == "run":
            output = await agent.run(args.prompt, project, budget)
            return {"mode": "run", "output": output, "usage": budget.summary()}
        # The SDK's __aenter__ probes before ownership is transferred; aclosing
        # also closes its HTTP client when that probe fails or is cancelled.
        benchmark = TSecBenchmarkAsync(
            base_url=config.benchmark_url,
            token=config.benchmark_token,
            timeout=config.timeout,
        )
        async with aclosing(benchmark):
            await benchmark.check_vpn()
            runner = BenchmarkRunner(
                benchmark,
                agent,
                project,
                budget,
                challenge_timeout=args.challenge_timeout,
                max_challenges=args.max_challenges,
                allow_hints=args.allow_hints,
            )
            return await runner.run()


async def run_application(args, config: Config) -> dict:
    task = asyncio.current_task()
    loop = asyncio.get_running_loop()
    received = None
    previous = {}

    def cancel(signum, frame):
        nonlocal received
        if received is None:
            received = signum
            loop.call_soon_threadsafe(task.cancel)

    for signum in (signal.SIGINT, signal.SIGTERM):
        previous[signum] = signal.signal(signum, cancel)
    try:
        async with asyncio.timeout(args.timeout):
            return await execute(args, config)
    except asyncio.CancelledError:
        if received is not None:
            raise Interrupted(received) from None
        raise
    finally:
        for signum, handler in previous.items():
            signal.signal(signum, handler)

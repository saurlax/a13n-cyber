"""Command-line interface for a13n Cyber."""

import argparse
import asyncio
import json
import logging
import platform
import sys

from . import __version__
from .config import Config
from .llm import smoke


def positive_int(value):
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("Must be a positive integer")
    return number


def parser():
    root = argparse.ArgumentParser(description="a13n Cyber autonomous security agent")
    root.add_argument("--version", action="version", version=__version__)
    commands = root.add_subparsers(dest="command")
    commands.add_parser("doctor", help="Validate configuration without network access")
    commands.add_parser("llm-smoke", help="Send one bounded model connectivity request")
    general = commands.add_parser("run", help="Execute a general task through Harness")
    general.add_argument("prompt", help="Task to execute")
    benchmark = commands.add_parser(
        "tsecbench", help="Run the TSecBench challenge loop"
    )
    for command in (general, benchmark):
        command.add_argument(
            "--workspace", default="work", help="Workspace directory (default: work)"
        )
        command.add_argument(
            "--agent-spec", help="SDK-native AgentSpec YAML or JSON file"
        )
        command.add_argument("--request-limit", type=positive_int, default=100)
        command.add_argument("--token-limit", type=positive_int, default=200_000)
        command.add_argument(
            "--timeout",
            type=positive_int,
            default=3600,
            help="Total execution deadline in seconds",
        )
    benchmark.add_argument("--challenge-timeout", type=positive_int, default=900)
    benchmark.add_argument("--max-challenges", type=positive_int)
    benchmark.add_argument(
        "--allow-hints", action="store_true", help="Expose hints that may reduce scores"
    )
    return root


def main(argv=None):
    root = parser()
    args = root.parse_args(argv)
    if args.command is None:
        root.print_help()
        return 0
    if args.command == "run" and not args.prompt.strip():
        root.error("Task prompt must not be empty")
    logging.basicConfig(
        level=logging.WARNING, format="%(levelname)s %(name)s %(message)s"
    )
    logging.getLogger("tsec_agent").setLevel(logging.INFO)
    try:
        config = Config.from_env()
        if args.command == "doctor":
            result = {
                "version": __version__,
                "python": platform.python_version(),
                "machine": platform.machine(),
                "config": config.public_summary(),
                "network_requests": 0,
            }
        elif args.command == "llm-smoke":
            result = smoke(config)
        else:
            from .application import run_application

            result = asyncio.run(run_application(args, config))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        # Provider bodies and SDK exception messages can contain credentials.
        category = type(exc).__name__
        exit_code = getattr(exc, "exit_code", 1)
        reason = "deadline" if isinstance(exc, TimeoutError) else category
        if category == "BudgetExhausted":
            reason = "budget_exhausted"
        print(json.dumps({"status": "failed", "reason": reason}), file=sys.stderr)
        return exit_code

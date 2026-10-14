import argparse
import json
import platform
import sys

from . import __version__
from .config import Config
from .llm import smoke


def main():
    parser = argparse.ArgumentParser(description="TSecBench preparation workspace; solver not implemented")
    parser.add_argument("command", choices=["doctor", "llm-smoke", "run"], nargs="?", default="doctor")
    args = parser.parse_args()
    if args.command == "run":
        print("Platform adapter and solver are pending. This image is not competition-ready.", file=sys.stderr)
        return 2
    try:
        config = Config.from_env()
        if args.command == "doctor":
            result = {"version": __version__, "python": platform.python_version(),
                      "machine": platform.machine(), "config": config.public_summary(),
                      "solver_ready": False, "network_requests": 0}
        else:
            result = smoke(config)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, RuntimeError, json.JSONDecodeError) as exc:
        # Validation messages do not contain supplied values.
        print(f"Configuration/request error: {exc}", file=sys.stderr)
        return 1

"""Human-readable presentation of redacted local execution records."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path


class ConsoleRenderer:
    def __init__(self, stream):
        self.stream = stream
        self.active = None

    def write(self, text):
        self.stream.write(text)
        self.stream.flush()

    def finish(self):
        if self.active is not None:
            self.write("\n")
            self.active = None

    def heading(self, label):
        self.finish()
        self.write(f"\n[{label}]\n")

    def value(self, value, indent=""):
        if isinstance(value, dict):
            for key, item in value.items():
                if isinstance(item, (dict, list)):
                    self.write(f"{indent}{key}:\n")
                    self.value(item, indent + "  ")
                else:
                    text = str(item).replace("\n", "\n" + indent + "  ")
                    self.write(f"{indent}{key}: {text}\n")
        elif isinstance(value, list):
            for item in value:
                self.write(f"{indent}- ")
                self.value(item, indent + "  ")
        else:
            self.write(f"{indent}{value}\n")

    def render(self, record):
        kind = record.get("event")
        data = record.get("data", {})
        if kind in {"part_start", "part_delta"} and "text" in data:
            channel = data.get("channel", "text")
            key = (record.get("run_id"), data.get("index"), channel)
            if kind == "part_start" or self.active != key:
                self.heading("Thinking" if channel == "thinking" else "Agent")
                self.active = key
            self.write(data["text"])
        elif kind == "part_end":
            if data.get("text"):
                self.write(data["text"])
            self.finish()
        elif kind == "function_tool_call":
            self.heading(f"Tool: {data.get('tool', 'unknown')}")
            self.value(data.get("arguments"))
        elif kind == "function_tool_result":
            self.heading(f"Result: {data.get('tool', 'unknown')}")
            self.value(data.get("result"))
        elif kind == "run_result":
            self.heading(f"Run {data.get('status', 'finished')}")
            usage = record.get("usage", {})
            self.write(
                f"Requests: {usage.get('requests', 0):,} | "
                f"Tokens: {usage.get('total_tokens', 0):,}\n"
            )
            if data.get("failure_code"):
                self.write(f"Failure: {data['failure_code']}\n")
        elif data.get("type") in {
            "run_started",
            "model_request_failed",
            "model_retry_scheduled",
        }:
            self.heading(data["type"].replace("_", " ").title())
            self.value({k: v for k, v in data.items() if k != "type"})


def view_logs(path, *, follow=False):
    source = Path(path)
    if source.is_dir():
        source = source / "agent.jsonl"
    renderer = ConsoleRenderer(sys.stdout)
    with source.open(encoding="utf-8") as reader:
        try:
            while True:
                position = reader.tell()
                line = reader.readline()
                if line.endswith("\n"):
                    renderer.render(json.loads(line))
                    continue
                if not follow:
                    break
                reader.seek(position)
                if source.stat().st_size < position:
                    renderer.finish()
                    reader.seek(0)
                time.sleep(0.2)
        finally:
            renderer.finish()

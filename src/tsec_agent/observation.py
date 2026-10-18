"""Local, explicitly enabled observation of the native Harness event stream."""

from __future__ import annotations

import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from a13n_harness import HarnessRunResultEvent
from a13n_harness.events import HarnessExtensionEvent
from a13n_harness.observation import redact_json
from pydantic_ai.messages import (
    FunctionToolCallEvent,
    FunctionToolResultEvent,
    PartDeltaEvent,
    PartEndEvent,
    PartStartEvent,
    TextPart,
    TextPartDelta,
    ThinkingPart,
    ThinkingPartDelta,
)

from .console import ConsoleRenderer


class EventTrace:
    def __init__(self, directory=None, *, console=False, secrets=()):
        self.directory = Path(directory).resolve() if directory else None
        self.secrets = tuple(sorted({s for s in secrets if s}, key=len, reverse=True))
        self.pending = {}
        self.file = None
        self.count = 0
        self.last_progress = 0.0
        self.renderer = ConsoleRenderer(sys.stderr) if console else None

    def __enter__(self):
        if self.directory:
            self.directory.mkdir(parents=True, exist_ok=True)
            self.file = (self.directory / "agent.jsonl").open(
                "a", encoding="utf-8", buffering=1
            )
        return self

    def __exit__(self, *args):
        # Never release an interrupted fragment that might be a secret prefix.
        self.pending.clear()
        if self.renderer:
            self.renderer.finish()
        if self.file:
            self.file.close()

    def clean(self, value):
        if isinstance(value, str):
            for secret in self.secrets:
                value = value.replace(secret, "[redacted]")
            return value
        if isinstance(value, dict):
            return {self.clean(str(k)): self.clean(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [self.clean(v) for v in value]
        if value is None or isinstance(value, (int, float, bool)):
            return value
        return f"<{type(value).__name__}>"

    def fragment(self, key, text):
        text = self.pending.pop(key, "") + text
        text = self.clean(text)
        keep = 0
        for secret in self.secrets:
            for length in range(1, min(len(secret), len(text) + 1)):
                if text.endswith(secret[:length]):
                    keep = max(keep, length)
        if keep:
            self.pending[key] = text[-keep:]
            return text[:-keep]
        return text

    def observe(self, item, usage):
        if not self.renderer and not self.file:
            return
        data = {}
        terminal = isinstance(item, HarnessRunResultEvent)
        if terminal:
            kind = "run_result"
            data["status"] = item.result.status
            if item.result.failure:
                data["failure_code"] = item.result.failure.code
            for key in list(self.pending):
                if key[0] == item.run_id:
                    self.pending.pop(key)
        else:
            event = item.event
            kind = getattr(event, "event_kind", type(event).__name__)
            if isinstance(event, HarnessExtensionEvent):
                kind = f"harness_{event.kind}"
                payload = event.payload
                if isinstance(payload, dict):
                    for key in (
                        "type",
                        "request_id",
                        "request_index",
                        "message_count",
                        "error_code",
                        "attempt",
                        "max_attempts",
                        "delay_seconds",
                    ):
                        if key in payload:
                            data[key] = payload[key]
            elif isinstance(event, (PartStartEvent, PartDeltaEvent)):
                part = event.part if isinstance(event, PartStartEvent) else event.delta
                if isinstance(
                    part, (TextPart, ThinkingPart, TextPartDelta, ThinkingPartDelta)
                ):
                    channel = (
                        "thinking"
                        if isinstance(part, (ThinkingPart, ThinkingPartDelta))
                        else "text"
                    )
                    text = (
                        getattr(part, "content", None)
                        or getattr(part, "content_delta", None)
                        or ""
                    )
                    data = {
                        "channel": channel,
                        "index": event.index,
                        "text": self.fragment((item.run_id, event.index), text),
                    }
                else:
                    data = {"index": event.index}
            elif isinstance(event, PartEndEvent):
                key = (item.run_id, event.index)
                data = {"index": event.index}
                if key in self.pending:
                    # The withheld suffix may be a truncated credential.
                    self.pending.pop(key)
                    data["text"] = "[redacted partial credential]"
            elif isinstance(event, FunctionToolCallEvent):
                arguments = event.part.args
                if isinstance(arguments, str):
                    try:
                        arguments = json.loads(arguments)
                    except json.JSONDecodeError:
                        arguments = "[invalid JSON arguments]"
                data = {
                    "tool": event.part.tool_name,
                    "tool_call_id": event.tool_call_id,
                    "arguments": "[omitted]"
                    if event.part.tool_name == "submit_flag"
                    else arguments,
                }
            elif isinstance(event, FunctionToolResultEvent):
                data = {
                    "tool": event.part.tool_name,
                    "tool_call_id": event.tool_call_id,
                    "result": event.part.content,
                }
        self.count += 1
        now = datetime.now(UTC).isoformat()
        counters = {
            "requests": usage.requests,
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
            "total_tokens": usage.total_tokens,
        }
        record = redact_json(
            self.clean(
                {
                    "time": now,
                    "run_id": item.run_id,
                    "sequence": item.sequence,
                    "event": kind,
                    "data": data,
                    "usage": counters,
                }
            )
        )
        if self.file:
            self.file.write(
                json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n"
            )
        if self.renderer:
            self.renderer.render(record)
        if self.directory and (terminal or time.monotonic() - self.last_progress >= 1):
            progress = {
                "updated_at": now,
                "run_id": item.run_id,
                "last_event": kind,
                "event_count": self.count,
                "usage": counters,
            }
            if terminal:
                progress["run_status"] = item.result.status
                if item.result.failure:
                    progress["failure_code"] = item.result.failure.code
            temporary = self.directory / "progress.tmp"
            temporary.write_text(
                json.dumps(progress, indent=2) + "\n", encoding="utf-8"
            )
            temporary.replace(self.directory / "progress.json")
            self.last_progress = time.monotonic()

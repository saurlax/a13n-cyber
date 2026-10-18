"""Verify the packaged toolkit without credentials, model calls, or network access."""

import asyncio
import json
import os
import shutil
import subprocess
import tempfile
from importlib.metadata import version
from pathlib import Path

os.environ["PWNLIB_NOTERM"] = "1"

from pwnlib.asm import asm
from pwnlib.elf import ELF
from pwnlib.util.cyclic import cyclic, cyclic_find
from pwnlib.util.packing import p32, u32
from pydantic_ai.messages import ToolReturnPart
from pydantic_ai.models.function import DeltaToolCall, FunctionModel

from tsec_agent.runtime import BUILTIN_ASSETS, Budget, CyberAgent


async def check_harness():
    async def respond(messages, info):
        assert "a13n-toolkit" in str(info.instructions)
        results = [
            p
            for message in messages
            for p in message.parts
            if isinstance(p, ToolReturnPart)
        ]
        if not results:
            call = (
                "view",
                {"file_path": "/environment/builtin/skills/a13n-toolkit/SKILL.md"},
            )
        elif len(results) == 1:
            assert "Packaged Toolkit" in str(results[-1].content)
            call = (
                "write",
                {
                    "file_path": "/environment/builtin/write-check.txt",
                    "content": "must not be written",
                },
            )
        elif len(results) == 2:
            assert (
                isinstance(results[-1].content, dict)
                and results[-1].content["ok"] is False
            )
            call = (
                "shell_exec",
                {
                    "command": "python -c 'import sys,pwnlib; print(\"toolkit-shell-ok\"); print(sys.executable)'"
                },
            )
        else:
            assert "toolkit-shell-ok" in str(results[-1].content)
            assert "/app/.venv/bin/python" in str(results[-1].content)
            yield "Offline toolkit verified"
            return
        yield {0: DeltaToolCall(name=call[0], json_args=json.dumps(call[1]))}

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        result = await CyberAgent(
            FunctionModel(stream_function=respond), project=root
        ).run(
            "Check the installed execution environment offline",
            root,
            Budget(request_limit=6),
        )
        assert result == "Offline toolkit verified"
    assert not (BUILTIN_ASSETS / "write-check.txt").exists()


def main():
    inventory = json.loads((BUILTIN_ASSETS / "toolkit.json").read_text())
    commands = [name for group in inventory["commands"].values() for name in group]
    missing = [name for name in commands if shutil.which(name) is None]
    if missing:
        raise RuntimeError(f"Missing packaged commands: {', '.join(missing)}")
    for command in (
        "curl",
        "jq",
        "rg",
        "git",
        "file",
        "nmap",
        "readelf",
        "objdump",
        "gdb",
        "gcc",
        "make",
    ):
        subprocess.run(
            [command, "--version"], check=True, capture_output=True, timeout=15
        )
    subprocess.run(["ffuf", "-V"], check=True, capture_output=True, timeout=15)
    for name in inventory["python_modules"]:
        __import__(name)
    assert u32(p32(0x12345678)) == 0x12345678
    assert cyclic_find(cyclic(32)[8:12]) == 8
    assert ELF("/bin/true", checksec=False).bits == 64
    assert asm("nop", arch="amd64") == b"\x90"
    assert Path(inventory["system_package_manifest"]).is_file()
    asyncio.run(check_harness())
    print(
        json.dumps(
            {
                "status": "ok",
                "network_requests": 0,
                "commands": len(commands),
                "pwntools": version("pwntools"),
                "builtin_skills": sorted(
                    p.parent.name
                    for p in (BUILTIN_ASSETS / "skills").glob("*/SKILL.md")
                ),
            }
        )
    )


if __name__ == "__main__":
    main()

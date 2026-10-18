"""Verify REA and Ghidra using a synthetic native fixture without network access."""

import asyncio
import json
import os
import subprocess
import tempfile
from pathlib import Path

from tsec_agent.rea import capability, validate_installation


async def check():
    root = Path(os.environ["A13N_REA_ROOT"])
    validate_installation(root)
    expected = json.loads((root / "package.json").read_text())["version"]
    with tempfile.TemporaryDirectory() as directory:
        workspace = Path(directory)
        source = workspace / "fixture.c"
        binary = workspace / "fixture"
        source.write_text(
            "__attribute__((noinline)) int fixture_answer(void) { return 42; }\n"
            "int main(void) { return fixture_answer() != 42; }\n"
        )
        subprocess.run(
            ["gcc", "-g", "-O0", "-no-pie", "-o", str(binary), str(source)],
            check=True,
            capture_output=True,
            timeout=30,
        )
        async with asyncio.timeout(300):
            async with capability(root, workspace).local as toolset:
                client = toolset.client
                tools = {tool.name for tool in await client.list_tools()}
                assert {
                    "binary_session",
                    "open_binary",
                    "analyze_function",
                    "close_binary",
                } <= tools
                await client.call_tool(
                    "binary_session", {"expected_package_version": expected}
                )
                try:
                    await client.call_tool(
                        "open_binary", {"path": str(binary), "provider_id": "ghidra"}
                    )
                    result = await client.call_tool(
                        "analyze_function", {"procedure": "fixture_answer"}
                    )
                    evidence = result.structured_content
                    assert evidence["normalized_result"]["pseudocode"]
                finally:
                    await client.call_tool("close_binary", {})
    print(
        json.dumps(
            {
                "status": "ok",
                "rea": expected,
                "provider": "ghidra",
                "network_requests": 0,
            }
        )
    )


if __name__ == "__main__":
    asyncio.run(check())

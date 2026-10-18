"""Local REA tools composed through the native MCP capability."""

import os
import shutil
from pathlib import Path

from fastmcp.client.transports import StdioTransport
from pydantic_ai.capabilities import MCP
from pydantic_ai.mcp import MCPToolset

from .config import ConfigurationError


def validate_installation(root: Path):
    if (
        not (root / "scripts/rea.mjs").is_file()
        or not (root / "skills/reverse-engineer-anything/SKILL.md").is_file()
    ):
        raise ConfigurationError(
            "A13N_REA_ROOT must select an installed rea-agents package"
        )
    if shutil.which("node") is None:
        raise ConfigurationError("REA requires Node.js on PATH")


def capability(root: Path, workspace: Path) -> MCP:
    environment = {
        key: value
        for key in (
            "PATH",
            "PATHEXT",
            "SystemRoot",
            "SYSTEMROOT",
            "COMSPEC",
            "HOME",
            "USER",
            "LOGNAME",
            "TEMP",
            "TMP",
            "TMPDIR",
            "LANG",
            "LC_ALL",
            "VIRTUAL_ENV",
            "TERM",
            "PWNLIB_NOTERM",
            "JAVA_HOME",
            "GHIDRA_INSTALL_DIR",
            "GHIDRA_HEADLESS_MAXMEM",
            "REA_GHIDRA_STARTUP_TIMEOUT_MS",
            "REA_ANALYSIS_PROVIDER",
        )
        if (value := os.environ.get(key)) is not None
    }
    return MCP(
        id="rea",
        local=MCPToolset(
            StdioTransport(
                command=shutil.which("node"),
                args=[str(root / "scripts/rea.mjs"), "mcp"],
                cwd=str(workspace.resolve()),
                env=environment,
                keep_alive=False,
                log_file=Path(os.devnull),
            ),
            id="rea",
            include_instructions=True,
            init_timeout=30,
            read_timeout=None,
        ),
        defer_loading=True,
    )

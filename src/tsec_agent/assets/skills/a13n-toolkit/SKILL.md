---
name: a13n-toolkit
description: Select and locate the CLI tools and Python libraries packaged with a13n Cyber when preparing to inspect files, services, or binaries, or diagnosing a missing command.
---

# Packaged Toolkit

Read `/environment/builtin/toolkit.json` for the basic container's tool inventory.
Use the existing `shell_exec` tool to run commands. No MCP server or nested agent
CLI is required to use this toolkit.

The inventory describes the Linux container. On another host, check the shell
dialect and executable availability before reusing Linux syntax. Prefer the
installed tool's `--help` over guessing flags or installing another version.

Use `python` from PATH for scripts: in the container it selects the application
virtual environment, including pwntools. If an import is missing on a source
installation, report the missing toolkit extra; do not silently change the host's
global Python environment.

Keep downloaded files, generated programs, and tool reports in the writable
workspace. The built-in mount supplies reference files and does not accept file
mutations. It is not a command working directory. Tools operate with the process's
existing permissions; package availability does not imply raw-socket, debugger,
container-runtime, or external-service access.

When comparing results between image builds, consult the OS package manifest
listed in the inventory and the project's uv lockfile. Report a missing dependency
or blocked operation separately from a negative finding.

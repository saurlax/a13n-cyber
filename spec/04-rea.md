# REA Integration

## Composition

REA is an optional local tool integration, not an agent runtime. `A13N_REA_ROOT` selects an installed `rea-agents` package directory containing `scripts/rea.mjs` and `skills/reverse-engineer-anything/SKILL.md`. An unset or empty value disables the integration. An explicitly selected invalid installation fails preparation; no automatic installation or alternate provider is attempted.

Both execution modes mount this package as the file-only, read-only `rea` Environment and discover its version-matched skill under `/environment/rea/skills`. The ordinary skill conflict policy applies. The complete upstream skill directory, including references, remains available on demand.

Each Run composes a native local MCP capability named `rea` launching Node with the installed entry point and `mcp`, with the current workspace as its working directory. Tool loading is deferred through the SDK. Harness owns connection entry, cancellation, and exit; the stdio transport does not keep a process alive after the Run. No second model loop, interactive setup, home-directory agent registration, or runtime package download occurs.

Application instructions identify the deferred capability and distinguish REA's absolute host paths from Harness virtual file paths. The MCP initialization timeout is 30 seconds; tool calls remain subject to the application's existing Run deadlines rather than an additional MCP read deadline.

The MCP subprocess receives only execution-related environment variables and explicit Ghidra/REA provider settings, excluding model and benchmark credentials. Its stderr is discarded to preserve the application's diagnostic-output contract. The integration grants host-process access through MCP; the read-only skill mount is not a sandbox for REA analysis tools. Targets and operations remain subject to the user's task authorization.

## Container

`Dockerfile.rea` extends a separately built basic image with Node.js, a full JDK 21, procps, REA, and Ghidra. npm dependencies are pinned by `integrations/rea/package-lock.json`. Ghidra's release URL and SHA256 are pinned in `integrations/rea/ghidra.json` and verified before extraction. Upstream package files and license notices remain installed. This image sets `A13N_REA_ROOT`, `GHIDRA_INSTALL_DIR`, `JAVA_HOME`, and `REA_ANALYSIS_PROVIDER=ghidra`; the basic image remains independent of REA.

`scripts/build-image.py --rea` builds the basic image as a local intermediate, builds the requested REA image, then runs the ordinary offline checks and `scripts/check-rea.py` with networking disabled before optional export. Model and benchmark configuration is still supplied only at runtime.

## Verification

Unit tests use synthetic workspaces and offline models to verify skill discovery, deferred native MCP composition, subprocess configuration, and disabled/invalid integration behavior. The container check connects to the actual REA MCP server, verifies its catalog and session discovery, and compiles a harmless native fixture to verify Ghidra decompilation without model calls or benchmark access. Container compatibility is established only by successfully running these checks in the built image.

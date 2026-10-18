# Repository Guide

a13n Cyber is a general-purpose autonomous security agent built on a13n Harness. Model providers and evaluation platforms are configurable dependencies or optional integrations, not the product's identity. The application owns integration lifecycles, scheduling, credentials, persistence, and recovery.

## Sources of Truth

- `README.md` owns user-facing setup, commands, and configuration.
- `spec/README.md` indexes accepted architecture and behavior contracts. Read the relevant contracts before implementation.
- `pyproject.toml` owns package metadata, Python requirements, dependencies, and entry points; `uv.lock` records dependency resolution.
- `src/tsec_agent/` owns implemented runtime behavior. Documentation must describe that behavior accurately.
- `tests/` owns automated behavioral checks; `Dockerfile` and `scripts/` own container packaging.
- Official platform contracts define benchmark behavior. Other teams' implementations are reference material, not platform specifications.

## Toolchain

Use Python 3.13 or later and uv. Use `uv sync --locked` to install the project and `uv run --locked` to execute commands. Manage dependencies through `uv add`, `uv remove`, and `uv lock`; commit dependency declarations and the lockfile together. Do not introduce pip installation instructions or require `PYTHONPATH` overrides.

Write repository automation scripts in Python, preferably with the standard library, and run them with `uv run --locked python`. Keep scripts portable across supported host platforms; do not add PowerShell, Bash, or batch script variants. Use `pathlib` for paths and argument lists with `subprocess` for external commands. Platform-specific behavior belongs only where the execution environment requires it.

Use Context7 for current library, SDK, API, and CLI documentation. If the relevant project is unavailable, consult its official documentation and source. Check APIs against the selected dependency version: a13n's website follows `main` and may differ from published packages.

## Engineering Boundaries

Before every implementation change, assess whether it introduces or changes a public command, configuration schema, component responsibility, lifecycle, integration contract, persistence format, or security boundary. If so, create or update the owning specification before coding. A focused bug fix that restores an existing contract, a private refactor, or a documentation correction does not require a new spec. Keep the specification, implementation, tests, and user documentation consistent within the same change.

Follow `spec/README.md` for specification ownership and management. Specifications describe accepted design in present-tense, testable language; they do not hold proposals, progress logs, or implementation checklists. Routine work does not require creating a GitHub Issue or PR, and this policy does not authorize external writes.

- Reuse Harness execution, tools, state, and capability interfaces rather than implementing a second model/tool loop.
- Prefer existing SDK interfaces and direct functions over custom frameworks or speculative abstractions. Validate external input at its owning boundary; avoid repeated validation and fallback paths without a concrete contract or failure case.
- Require explicit `LLM_BASE_URL`, `LLM_MODEL`, and `LLM_API_KEY`. Do not introduce model/provider defaults or vendor-specific credential fallbacks. Keep repository and package descriptions focused on the general-purpose agent.
- Keep platform adapters, agent composition, model configuration, and outer scheduling separate. Platform lifecycle and success verification belong to application code.
- Keep stable agent definitions separate from current Run bindings and portable continuation state. Do not serialize credentials, live clients, or environment handles into state or metadata.
- Treat skills as procedural content, MCP as a tool integration, and CLI binaries as execution-environment dependencies. A skill does not install tools or grant permissions.
- Configure explicit request budgets, deadlines, and cleanup. Child-agent budgets do not automatically enforce an application-wide budget.
- Reconcile uncertain external outcomes before retrying mutations. Saving Harness state does not make platform operations exactly once.
- Preserve unrelated changes. Do not commit, push, publish, or deploy unless authorized by the user.

## Documentation

Write canonical documentation, code comments, and contributor instructions in English. Keep README content focused on the product, working commands, configuration, and architecture. Use Mermaid when a diagram clarifies implemented relationships. Do not present proposed functionality as available.

Keep development diaries, dated progress reports, conversation transcripts, and temporary handoff notes out of permanent repository documentation. Do not add placeholder badges, unsupported claims, or links to nonexistent files.

## Credentials and Execution

Keep credentials outside version control and container layers. Use environment variables and untracked local environment files; examples must contain no real secrets. Logs and diagnostics must not expose credentials or provider error bodies that may echo them.

Offline diagnostics and unit tests must not call models or benchmark targets. Model connectivity checks must remain explicit and bounded. Run security tooling only against targets authorized for the task.

## Validation

Run checks appropriate to the changed behavior:

```bash
uv sync --locked
uv run --locked --env-file .env a13n-cyber doctor
uv run --locked python -m unittest discover -s tests -v
uv run --locked ruff check .
uv run --locked ruff format --check .
git diff --check
```

For offline diagnostics, explicitly supply the three required model variables; test-only values are sufficient because `doctor` performs no network requests. For container changes, build the image and run `doctor` with `--network none` and explicit configuration when Docker is available. Verify documentation commands against the actual CLI. Report checks that could not run; do not claim untested model or platform compatibility.

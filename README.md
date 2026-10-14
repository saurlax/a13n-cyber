# a13n Cyber

[![Python](https://img.shields.io/badge/python-3.13%2B-blue)](https://www.python.org/)
[![uv](https://img.shields.io/badge/dependencies-uv-de5fe9)](https://docs.astral.sh/uv/)

**An autonomous security agent built on a13n Harness.**

a13n Cyber runs general security tasks and TSecBench evaluations through the same embedded agent. It combines workspace tools, procedural skills, MCP capabilities, and an OpenAI-compatible Chat Completions model, with StepFun as the default provider.

```mermaid
flowchart LR
    CLI[a13n Cyber CLI] --> Task[General task]
    CLI --> Runner[TSecBench runner]
    Runner <--> SDK[TSecBench SDK]
    SDK <--> Platform[Platform API]
    Task --> Agent[Cyber Agent]
    Runner --> Agent
    Agent --> Harness[a13n Harness]
    Harness <--> Model[Chat Completions model]
    Harness --> Tools[Files and shell]
    Harness --> Skills[Project skills]
    Harness --> MCP[MCP tools]
```

- **Run a task.** Give the agent a prompt and a workspace with file and command tools.
- **Evaluate on TSecBench.** Fetch challenges, start targets, submit flags, and release environments automatically.
- **Compose capabilities.** Load SDK-native agent instructions and MCP configuration, and discover project skills.

## Work from source

You need **Python 3.13 or later** and **[uv](https://docs.astral.sh/uv/getting-started/installation/)**.

```bash
git clone https://github.com/saurlax/a13n-cyber.git
cd a13n-cyber
uv sync --locked
uv run --locked a13n-cyber doctor
```

`doctor` validates configuration offline and prints a JSON summary with credential-presence booleans.

## Run an agent

Copy `.env.example` to `.env` and set `STEPFUN_API_KEY`. Then run a task:

```bash
uv run --locked --env-file .env a13n-cyber run "Inspect the files and summarize the application architecture" --workspace ./work
```

The workspace is created if absent. Shell execution uses PowerShell on Windows and Bash or sh on Unix, with the current process's authority. Direct Local execution is not an OS sandbox.

Bound execution explicitly when needed:

```bash
uv run --locked --env-file .env a13n-cyber run "Analyze the application" --workspace ./work --request-limit 50 --token-limit 100000 --timeout 600
```

Both modes default to 100 model requests, 200,000 total tokens, and a 3,600-second execution deadline. Benchmark challenges share the invocation's request and token allowances. Token accounting follows provider-reported usage; limits are not a currency budget.

## Run TSecBench

For local evaluation, obtain a task's `BENCHMARK_BASE_URL` and `BENCHMARK_TOKEN` from the platform and connect its VPN before starting:

```bash
uv run --locked --env-file .env a13n-cyber tsecbench --workspace ./work --max-challenges 2 --challenge-timeout 900
```

The runner uses the official SDK to check VPN connectivity and process incomplete challenges sequentially. Each challenge gets a separate working directory and a fresh Harness Run. The agent receives challenge-scoped `submit_flag` and `get_progress` tools. `--allow-hints` additionally exposes `get_hint`; requesting hints can reduce scores.

The runner closes a target after completion, failure, timeout, or cancellation. It refreshes platform progress instead of treating the agent's final text as proof of success. Local execution ends after the selected challenge pass, all challenges complete, or a stop condition occurs. Exiting the container does not assert that the platform has finalized the evaluation.

Standard output contains the final JSON result. Standard error contains application lifecycle events and safe error categories. An incomplete challenge pass can finish normally; use `completed_challenges` and `stop_reason` to interpret the result.

## Customize the agent

Load SDK-native AgentSpec YAML or JSON with `--agent-spec`:

```bash
uv run --locked --env-file .env a13n-cyber run "Review the evidence" --workspace ./work --agent-spec agents/analyst.yaml
```

The same option works with `tsecbench`. AgentSpec supplies instructions, model settings, and supported capabilities, including native MCP declarations. Model selection remains in environment configuration; deadlines and usage limits remain application-owned. Harness UI resource files such as `mcp_servers` catalogs are a different format.

Place skills under the selected workspace:

```text
work/.agents/skills/
  investigation/
    SKILL.md
    references/
```

Each `SKILL.md` has YAML frontmatter with `name` and `description`. General Runs discover skills under `/workspace/.agents/skills`. Benchmark Runs read the same project's skills through a file-only project mount while writing to separate challenge directories. Skills supply instructions; install their required CLI binaries and MCP servers separately in the execution environment.

See the [Harness MCP guide](https://a13n.dev/docs/a13n-harness/mcp/) for native declarations compatible with the installed SDK.

## Configure models and credentials

The default model is `step-5-preview` at the Step Plan Chat Completions endpoint. Settings come from the process environment; uv and Docker can load an untracked `.env` file.

| Variable | Default | Purpose |
| --- | --- | --- |
| `LLM_BASE_URL` | `https://api.stepfun.com/step_plan/v1` | Chat Completions API base URL |
| `LLM_MODEL` | `step-5-preview` | Model identifier |
| `STEPFUN_API_KEY` | Unset | Model credential; takes precedence over `LLM_API_KEY` |
| `LLM_API_KEY` | Unset | Alternative model credential |
| `LLM_REASONING_EFFORT` | `high` | `low`, `medium`, or `high` |
| `LLM_REQUEST_TIMEOUT` | `60` | Provider and platform request timeout in seconds |
| `LLM_MAX_OUTPUT_TOKENS` | `512` | Output limit for the connectivity check only |
| `BENCHMARK_BASE_URL` | Unset | Required platform endpoint for TSecBench mode |
| `BENCHMARK_TOKEN` | Unset | Required evaluation task credential |

For a standard pay-as-you-go StepFun account, use `https://api.stepfun.com/v1`. Hosted TSecBench supplies benchmark credentials automatically; configure the permitted model gateway and model credential on its submission page. Runtime dependencies must be installed in the image before evaluation.

To make one bounded connectivity request:

```bash
uv run --locked --env-file .env a13n-cyber llm-smoke
```

The check consumes model quota. It does not retry automatically or print model content. Unit tests and `doctor` do not require credentials.

## Build a container

Docker builds install production dependencies with `uv sync --locked --no-dev --no-editable`. The image starts TSecBench mode by default.

```bash
docker build --platform linux/amd64 -t a13n-cyber:dev .
docker run --rm --network none a13n-cyber:dev doctor
docker run --rm --env-file .env a13n-cyber:dev
```

Override the default command for a general task:

```bash
docker run --rm --env-file .env a13n-cyber:dev run "Inspect the workspace" --workspace /app/work
```

On Windows, the build script also runs the offline diagnostic:

```powershell
./scripts/build-image.ps1
./scripts/build-image.ps1 -Export
```

`-Export` writes `dist/a13n-cyber.tar` and prints its SHA256 digest. Override the base image with `-PythonBaseImage` or Docker's `PYTHON_BASE_IMAGE` build argument. Local benchmark containers still need connectivity to the platform's target network.

## Development

| Task | Command |
| --- | --- |
| Install the locked environment | `uv sync --locked` |
| Run offline diagnostics | `uv run --locked a13n-cyber doctor` |
| Run tests | `uv run --locked python -m unittest discover -s tests -v` |
| Lint Python | `uv run --locked ruff check .` |
| Check formatting | `uv run --locked ruff format --check .` |
| Update the dependency lock | `uv lock` |

Read the [specification catalog](spec/README.md) before changing public behavior or architecture. [AGENTS.md](AGENTS.md) defines repository conventions. Application code lives in `src/tsec_agent/`, tests in `tests/`, and container tooling in `scripts/`.

## Resources

- [a13n Harness documentation](https://a13n.dev/docs/a13n-harness/)
- [Agent Foundation](https://github.com/converge-ai-labs/agent-foundation)
- [TSecBench integration guides](https://tsecbench.zc.tencent.com/#integration)

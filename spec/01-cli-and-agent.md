# CLI and Agent Execution

## Commands

- `a13n-cyber doctor` validates explicitly supplied configuration offline and prints runtime metadata and credential-presence booleans. Missing required configuration fails with exit code 1 without network access.
- `a13n-cyber llm-smoke` sends one bounded connectivity request.
- `a13n-cyber run PROMPT` executes a nonempty user task through Harness.
- `a13n-cyber tsecbench` runs the platform lifecycle defined in [TSecBench](02-tsecbench.md).
- Bare invocation prints help without executing a model or benchmark request.

Both execution modes accept `--workspace`, `--agent-spec`, `--request-limit`, `--token-limit`, and `--timeout`. TSecBench additionally accepts `--challenge-timeout`, `--max-challenges`, and `--allow-hints`. Numeric limits are positive. The default root deadline is 3600 seconds, request limit is 100, token limit is 200000, and per-challenge deadline is 900 seconds. TSecBench applies remaining request and token allowances across fresh challenge Runs; it does not reset the total allowance for each challenge.

Exit code 0 means normal local completion, including an exhausted selected challenge pass. Code 1 means configuration, execution, deadline, or cleanup failure. Code 2 is an argument error. SIGINT and SIGTERM cancel active work, run cleanup, and exit with 130 and 143 respectively. Local completion does not assert platform-wide success.

## Composition

The model uses explicit `OpenAIChatModel` and `OpenAIProvider`. `LLM_BASE_URL`, `LLM_MODEL`, and `LLM_API_KEY` are all required process environment variables. Unset, empty, or whitespace-only values fail before model-client construction or platform requests. There are no provider defaults, model defaults, or vendor-specific credential aliases. Invalid URLs and missing-variable errors never echo supplied values. Help and version commands do not require model configuration.

Request timeout follows `LLM_REQUEST_TIMEOUT`. Reasoning effort is omitted unless `LLM_REASONING_EFFORT` is explicitly supplied; the application does not automatically request a vendor-specific reasoning mode. Connectivity output limits remain separate from agent output settings. Containers include no model connection configuration and default to CLI help; task and integration commands are explicitly selected at invocation.

An optional SDK-native AgentSpec file supplies instructions and capabilities, including supported declarative MCP. It is not Harness UI configuration. Application-owned model, deadline, usage, and base instruction policy take precedence. The spec cannot select an alternative model. Unknown or invalid spec fields fail preparation.

Programmatic composition accepts additional native Capability instances and passes them through the Harness builder. Native runtime objects such as in-process MCP servers belong to this Python composition surface, not to the serialized AgentSpec schema.

The agent exposes Harness file and shell tools for the selected workspace. General mode scans `/workspace/.agents/skills`. Benchmark Runs mount the CLI workspace as a file-only project source and scan `/environment/project/.agents/skills`; their writable working directories remain separate. No user-home skill scan or automatic tool installation occurs. CLI binaries must already exist in the execution environment. Shell subprocesses inherit only execution-related environment variables, excluding model and platform credentials. Each Run has fresh bindings and message state. TSecBench adds only current-challenge platform tools.

## Output

Standard output contains the final JSON result; standard error contains bounded application lifecycle events without prompts, model output, flags, or secrets. General output includes the agent's final text and usage. Benchmark output includes authoritative challenge progress and the local stop reason. Exceptions are reported by safe category rather than raw provider or SDK messages.

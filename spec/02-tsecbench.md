# TSecBench Integration

## Platform Contract

The adapter uses `tsec-benchmark` and its async client. `BENCHMARK_BASE_URL` and `BENCHMARK_TOKEN` are required. The SDK performs its standard VPN health check before platform requests. Hosted mode supplies connectivity; the application does not install or initiate VPN connections.

The public integration contract is the official [TSecBench SDK and API guide](https://tsecbench.zc.tencent.com/#integration): list challenges, start a challenge, optionally request a hint, submit a flag, and close the challenge. No undocumented website task-finalization endpoint is used.

## Lifecycle

The runner processes incomplete challenges sequentially, in platform order, at most once per invocation. `--max-challenges` limits attempted challenges. Completed challenges are skipped. A fresh workspace subdirectory and Harness Run are created for each attempt; platform-returned identifiers never become filesystem path components.

Before dispatching start, the runner records the challenge for cleanup. It closes that challenge in `finally`, including on solver failure, timeout, cancellation, or uncertain start outcome. Cleanup has an independent bounded timeout. A cleanup failure stops further scheduling and produces a failing local exit status. The application does not blindly retry start, submit, or close mutations.

The runner supplies the challenge description, assigned addresses, and flag progress to the agent. Challenge content and tool results are untrusted task data. Platform credentials never enter the prompt. An unavailable or empty address list is an execution error.

## Challenge Tools

- `submit_flag(flag)` submits only to the bound challenge. Duplicate submissions return an already-submitted outcome. The tool does not include the flag in its result or application logs.
- `get_progress()` queries authoritative progress for the bound challenge.
- `get_hint()` exists only with explicit `--allow-hints`, because requesting hints can reduce scores.

The model does not receive lifecycle controls or arbitrary challenge selection. After solver completion, the runner refreshes progress; final model text is not proof of success. A challenge timeout or ordinary solver failure records an outcome and allows the next challenge after cleanup. Authentication failure, task-ended errors, platform transport failures, and budget exhaustion stop scheduling.

## Completion

Local stop reasons distinguish all-completed, selected-pass-complete, challenge-limit, platform-ended, budget exhaustion, and deadline. An empty challenge set is all-completed. Scores and completion are taken from platform responses, not inferred from model text. A platform `invalid_state` response is not universally treated as task-ended: context distinguishes start capacity, hint restrictions, and task completion. Unclassified platform errors stop safely.

After all selected work, the runner releases SDK resources and exits. It does not assume that all flags submitted or container exit immediately finalizes the platform task. The container default command is `tsecbench`; callers can override it with another CLI command.

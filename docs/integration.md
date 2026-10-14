# 接入记录与待核实项

## StepFun：已确认

官方 [Step 5 Preview 文档](https://platform.stepfun.com/docs/zh/guides/models/step-5-preview)（2026-10-14 读取）列出模型 ID `step-5-preview`、1M 上下文、64k 最大输出、工具调用、`reasoning_effort` 的 low/medium/high。

官方 [开放平台首页](https://platform.stepfun.com/) 示例使用 `https://api.stepfun.com/v1` 的 Chat Completions 接口。本仓库用标准库发送兼容请求，暂不依赖某个 SDK。

**套餐入口已确认**：[Step Plan 文档](https://platform.stepfun.com/docs/zh/step-plan/overview) 列出 Chat Completions 的 Base URL 为 `https://api.stepfun.com/step_plan/v1`，并列出 `step-5-preview`。默认配置已采用套餐入口。Messages/Anthropic 格式另用 `https://api.stepfun.com/step_plan`。本次没有读取账户、寻找密钥、调用付费 API 或使用任何套餐额度。账户实际权限与托管网关兼容性仍需联调。

Context7 检索未找到匹配的 StepFun 文本 API 文档，因此转读官方页面；不使用图像/音频项目文档代替。

## TSecBench：参考证据，不是当届官方契约

[BLHX Dockerfile](https://github.com/wablhx/BLHX/blob/main/Dockerfile) 与 [runner](https://github.com/wablhx/BLHX/blob/main/agent/runner.py) 显示其采用环境变量、平台网关、预装工具和 list/start/submit/close 流程。[Cruiser](https://github.com/TJR181/Cruiser-Agent) 也有相同生命周期。

当前骨架为 linux/amd64。以下尚未核实，**不按第三方实现直接定案**：

- 本届镜像格式、大小、CPU/内存、启动命令及是否以 root 运行。
- StepFun 的托管网关准确 URL、密钥转发、套餐入口支持。
- `BENCHMARK_BASE_URL` / `BENCHMARK_TOKEN` 当届注入方式、API 路径与响应 schema。
- 是否同时提供 Kali/SSH 环境，哪些工具要打进 Agent 镜像。
- 原始模型对话/工具调用记录的指定日志格式和保存位置。
- 赛前测试与正式初赛的提交次数、并发题目上限、单题预算。
- AI-KOH 决赛的控制权 API / 计分协议；不会把线上解题接口当作决赛接口。

## 骨架选择

用 Python 标准库做配置与连接检查，减少第一版构建的不确定性；求解引擎尚未决定。默认 `doctor` 无网络，`run` 明确失败，避免把未实现的镜像误认为能自动解题。LLM 连通性命令只返回用量元数据，不输出密钥或模型原文。

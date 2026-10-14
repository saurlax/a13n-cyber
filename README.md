# TSecBench / StepFun Agent 工作区

2026-10-14 建立。模型选用 StepFun **`step-5-preview`**（官方 ID，不是 `stepfun-5-preview`）。

当前交付是 Git 仓库与容器准备骨架：离线配置检查、一次模型连通性检查、镜像构建脚本和参考仓库研究。**尚未实现平台调度、解题工具与 Agent 循环，不能作为正式参赛镜像提交。**

## 结构

```text
src/tsec_agent/   配置、CLI、模型连通性检查
scripts/         Windows 镜像构建与导出
tests/           密钥不泄漏和配置校验
docs/            仓库研究、接入待办
Dockerfile       linux/amd64 单容器骨架
.env.example     本地模型配置示例
.env.hosted.example  托管配置待填模板
```

## 无密钥离线检查

在仓库目录执行：

```powershell
$env:PYTHONPATH = 'src'
python -m tsec_agent doctor
python -m unittest discover -s tests -v
```

如果系统 Python 不可用，可用 Docker：

```powershell
./scripts/build-image.ps1
docker run --rm --network none tsec-step-agent:dev doctor
```

若 Docker Hub 无法连接，可通过 `-PythonBaseImage public.ecr.aws/docker/library/python:3.12-slim-bookworm` 使用公开镜像副本；此参数不修改 Docker 全局镜像源。

`doctor` 不请求模型或靶场，不需要密钥。输出只显示密钥是否配置。

## StepFun 连通性检查（会消耗模型额度）

复制 `.env.example` 为 `.env`，在本地编辑密钥。Python CLI 不会自动加载 `.env`；本地直接运行需设置环境变量，Docker 可加载文件：

```powershell
docker run --rm --env-file .env tsec-step-agent:dev llm-smoke
```

它只发送一次「Reply with OK only」，默认最大输出 512 tokens、60 秒超时，不自动重试。默认地址是官方 Step Plan 的 Chat Completions 入口 `https://api.stepfun.com/step_plan/v1`；普通按量 API 是 `https://api.stepfun.com/v1`。未填 Key 会直接失败。实际账户模型权限和托管网关支持还需联调。

托管时将 `LLM_BASE_URL` 改为平台提供的 StepFun 网关入口。不会根据其他队伍的 DeepSeek 网关猜地址。`BENCHMARK_BASE_URL` / `BENCHMARK_TOKEN` 保留用于接入，当前尚不请求平台。

## 导出

```powershell
./scripts/build-image.ps1 -Export
```

生成 `dist/tsec-step-agent.tar` 和 SHA256。这仍是准备镜像，不是解题镜像；最终压缩格式、启动参数、日志格式等需按当届托管要求核实。

## 下一步

1. 用 Step Plan Key 核实账户模型权限、托管网关连通性和实际额度限制。
2. 核实官方平台 API/SDK、镜像限制、凭据注入、完整日志要求。
3. 实现单题生命周期：获取题目 → 启动靶场 → 解题 → 平台验证 → finally 关闭靶场。
4. 实现单 Agent 工具循环，增加题目超时、步数上限、错误恢复和结构化日志。
5. 用少量授权测试题验证，再决定是否增加并发或多 Agent。

研究资料见 [参考仓库](docs/repositories.md) 和 [接入记录](docs/integration.md)。本仓库只包含原创骨架，没有复制第三方解题源码。

# 公开仓库研究

检索日期：2026-10-14。已阅读官方导航与下列公开项目说明；未运行第三方 Agent，也未将其源码引入本仓库。往届项目和其他赛事的 TSecBench 项目不能直接视为本届 AI-KOH 参赛作品。

| 仓库 | 关系 | 最值得参考的部分 |
| --- | --- | --- |
| [Yeti-791/Tsec-Hackathon](https://github.com/Yeti-791/Tsec-Hackathon) | 自述为官方赛事资源仓，列出往届优秀队伍 | 项目导航、答辩资料、复盘；旧赛事规则不当作本届规则 |
| [m-sec-org/BreachWeave](https://github.com/m-sec-org/BreachWeave) | 官方导航收录第二届 ai小分队项目 | Manager / Observer / Solver 分工与上下文管理 |
| [oritera/Cairn](https://github.com/oritera/Cairn) | 官方导航收录第二届 Bytex 项目 | 黑板协作、任务分解、状态空间搜索；不是低预算现成模板 |
| [chainreactors/tinyctfer](https://github.com/chainreactors/tinyctfer) | 官方导航收录首届 Antix 项目 | 极简 runtime 与工具设计，适合先理解最小 Agent |
| [TJR181/Cruiser-Agent](https://github.com/TJR181/Cruiser-Agent) | 面向 TSecBench 的完整 Agent；官方导航另有首届 Cruiser 项目链接 | 平台生命周期、并发限额、分层调度、平台确认成功；依赖 Claude CLI 的部分需重新适配 StepFun |
| [wablhx/BLHX](https://github.com/wablhx/BLHX) | README 表明是百度 Agent+ 挑战赛作品，使用 TSecBench | Dockerfile、托管环境变量、runner；不可误称腾讯本届战队 |
| [Yean-Sec/StrikeAgent_AtkBrain-Flash](https://github.com/Yean-Sec/StrikeAgent_AtkBrain-Flash) | TSecBench 项目，README 自报成绩 | 长程自循环、完整部署；多组件系统不宜直接照搬成单容器 |
| [MingyiSecLab/tsec-zeroAgent](https://github.com/MingyiSecLab/tsec-zeroAgent) | 自述第二届腾讯赛事工具包 | 往届接口接入，但接口与本届托管要求需重新核实 |

## 我们先采用的结构

先做「平台 adapter + 单 Agent 工具循环 + 可换模型 provider + 有上限的任务 runner」。容器内预装实际需要的依赖，启动后靠环境变量接入。平台调度和求解分开，避免把 API 路径、模型网关和密钥写死在提示词里。

优先读 tinyctfer 理解最小循环、Cruiser 理解平台调度、BLHX 理解托管打包；再读 BreachWeave / Cairn 的高级协作。先跑通少量测试题，再判断是否需要复杂架构。

## 复用检查

采用第三方代码前查对应仓库当前 LICENSE、依赖许可和具体版本；本次没有为任何项目推定许可。赛程、当届组队/复用要求以腾讯官方为准。研究源码不是授权运行它的完整安全测试工具。

# Upstream Audit

审计基线：`chenchen1010/hermes-media-suite` 的 `master` 分支，commit `1e417b6dba5a1b5d951d2af48823d3fee29fcc44`。

## 结论

Upstream 是一套可安装的 Hermes 能力包，不是完整业务应用。它只有 6 个文本/代码文件：安装提示、部署文档、两个 Profile 和一个零依赖 TikHub MCP。不存在数据库、领域模型、Research Engine、测试、CI 或容器配置。因此改造应保持 additive：底层采集与转录能力原样保留，新建独立 Career Intelligence 层。

## REUSE

| 能力 | 决策 |
| --- | --- |
| `mcp/tikhub_xhs_mcp.py` | 原样保留为 Social Provider；20 个工具已通过 JSON-RPC `initialize` / `tools/list` 冒烟 |
| `profiles/social-research.md` | 保留为社媒采样与底层工具使用规范 |
| `profiles/media-transcriber.md` | 保留字幕优先、ASR 兜底和分享式提纯标准 |
| ffmpeg / yt-dlp / faster-whisper | 复用现有媒体链路，不进入 Career 核心包 |
| TikHub 24h `cache_url` | 作为 Provider 缓存第一层，后续加内容哈希与本地索引 |
| Hermes Profiles / MCP / Skills | 作为运行时能力，不在本仓库重造 Agent 框架 |

## MODIFY

| 项目 | 修改方向 |
| --- | --- |
| README | 补充 fork 血缘、当前完成度、验证命令和路线图 |
| `social-research` 文档 | 文首写“14 个工具”，实际是 20 个；后续统一为自动生成的工具清单 |
| Hermes 编排 | Profile 状态相互隔离；Career 数据存外部 SQLite/Postgres，由 Career Orchestrator 统一读取 |
| 飞书接入 | 当前 Hermes 已有 Feishu/Lark channel；聊天通道优先原生接入，文档写入再评估 lark-cli |
| MCP 暴露 | 20 个 TikHub 工具仅给 Social Research Worker；外部只暴露 8–12 个 Career 高层工具 |
| 错误处理 | TikHub 原始 HTTP body 不应直接进入最终日志；生产阶段增加脱敏和长度限制 |

## ADD

- `hermes_career_intelligence` Python 包与 Pydantic 领域模型。
- Claim → Evidence → Content/Transcript 时间戳的可逆追踪。
- User Profile 与 User Observation 分离的更新流程。
- Creator Ranking、Research Ranking、Query Expansion 与 ASR 选择策略。
- Consensus、Disagreement、Emerging Signal、Gap Analysis 和 ResearchPack。
- SQLite 开发存储；部署阶段提供 Postgres 迁移路径。
- MockSocialProvider、离线 acceptance demo、单元/集成测试。
- Career Researcher Profile、精简 MCP Surface、部署与安全文档。

## REMOVE

当前不删除 upstream 代码。只在真实测试证明某项能力不可用、重复或不安全时弃用，并保留迁移说明。

## Hermes 官方能力对架构的影响

- Profiles 的配置、Memory、Sessions 与 Skills 相互隔离，所以共享求职知识不能依赖某个 Profile 的内部 Memory。
- Skills 采用按需加载，适合放研究步骤和输出规范，减少常驻上下文。
- MCP 支持每个 server 的工具过滤，适合把底层 20 工具限制在 Social Worker。
- 多 Profile 的长期协作可用 Hermes Kanban；研究运行状态仍以业务数据库为准。
- Scheduling 用于定期增量研究，不做每日全量抓取。

官方参考：[Profiles](https://hermes-agent.nousresearch.com/docs/user-guide/profiles)、[Skills](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills)、[MCP](https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp)、[Documentation](https://hermes-agent.nousresearch.com/docs/)。


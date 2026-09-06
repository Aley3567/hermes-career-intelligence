# Hermes Career Intelligence

基于 [chenchen1010/hermes-media-suite](https://github.com/chenchen1010/hermes-media-suite) 的证据优先个人求职情报系统。

项目保留 upstream 的四平台 TikHub MCP、`social-research` 与 `media-transcriber`，新增平台无关的 Career Intelligence 层：User Profile、Claim/Evidence、Creator 评分、共识/分歧/新兴信号、Skill Gap、ResearchPack 与持久化。

当前状态：Stage 0–3 已完成代码与离线/fixture 验收；真实 TikHub Key 冒烟测试仍需在部署/Pilot 前执行。Stage 4 的输入输出契约、证据不变量、实施顺序和 golden fixture 测试矩阵已准备完成，下一步从 4A Ranking 开始实现。Mock/fixture 结果不会被当成真实平台结论。

## 本地验证

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
python -m unittest discover -s tests -v
python -m hermes_career_intelligence.demo
```

详细设计与后续阶段：

- [Upstream 审计](docs/AUDIT.md)
- [架构](docs/ARCHITECTURE.md)
- [分阶段路线图](docs/ROADMAP.md)
- [Social Provider Contract](docs/PROVIDERS.md)
- [缓存与成本纪律](docs/CACHING.md)
- [Stage 4 Intelligence Engine Contract](docs/INTELLIGENCE_ENGINE.md)
- [待创建的 GitHub Issues](docs/GITHUB_ISSUES.md)

## Upstream 原始能力

一台109一年的云服务器 + Hermes，跑起两个真能干活的 agent：

1. **音视频转录整理**：丢一个链接/文件给它，还你一份提纯过的中文文稿（不是三句话摘要）。
   整理标准的思路来自生财有术亦仁分享的「小D」agent，在此致谢；本仓库是社区重写与升级版。
2. **四平台社媒调研**：小红书、抖音、微信公众号、微信视频号——丢链接直取内容，
   关键词跨平台搜索，挖评论区，拆对标账号。

两个 agent 拼起来是一条"收藏处理流水线"：平时随手扔进群里的链接
（公众号文章、抖音视频、小红书笔记、视频号），agent 拉回内容、转录整理、归档——
把"收藏了从没看过"变成"收藏了就有输出"。

它们跑在服务器上，不绑你的电脑。电脑关机，agent 照样干活；
在微信或者飞书里发条消息就能使唤。

### 原始仓库结构

```
INSTALL_PROMPT.md             一键安装提示词：复制丢给 Codex/Claude Code，替你装完整套
mcp/tikhub_xhs_mcp.py         TikHub 四平台采集 MCP（零依赖，20 个工具，主链路真实调用验证过）
profiles/media-transcriber.md 转录整理 agent 的指令
profiles/social-research.md   四平台社媒调研 agent 的指令
docs/deploy-cheap-server.md   从买服务器到跑通的完整教程
```

### 原始套件快速开始

打开 [INSTALL_PROMPT.md](INSTALL_PROMPT.md)，把前置资料备齐、提示词填好，
丢给你的 Codex / Claude Code，它替你装完整套。

### 原始套件成本

| 项目 | 花费 |
| --- | --- |
| 服务器 | 一百元上下一年（入门轻量云主机） |
| 大模型 | 自己的 key，用多少花多少（deepseek 性价比高；有 ChatGPT 会员也可接入共享额度） |
| TikHub | 按调用计费，只在用社媒调研时产生；响应带 24h 免费 cache_url。注册入口：[user.tikhub.io/register?ref=EJ7Ka9h8](https://user.tikhub.io/register?ref=EJ7Ka9h8)（带我的推荐码，不加价，介意可去掉 ref 参数） |

软件本身全部免费开源。

### 为什么保留策展后的 TikHub MCP？

TikHub 有官方 MCP 生态（托管版 mcp.tikhub.io、`pip install tikhub-mcp` 自托管版、桌面打包代理），
服务器上不是不能跑。没用它的原因是不合身：官方版本面向全平台通用（13+ 平台、上千个端点的家底），
工具一多，agent 选起来又慢又容易错。这里是为「收藏处理 + 社媒调研」场景策展的 20 个工具——
中文描述、贴分享口令就能用、图文视频自动回退、花钱纪律写进指令——而且零依赖单文件，
你花五分钟就能把代码审完。需要更多平台的，用官方的：github.com/TikHub。

## 致谢与血缘

- [Hermes](https://github.com/NousResearch/hermes-agent) —— 底座 agent 框架（本仓库与 Nous Research 无关联，仅为使用者）
- [hermes-media-suite](https://github.com/chenchen1010/hermes-media-suite) —— 本项目的 upstream，MIT License
- 生财有术 · 亦仁的「小D」转录整理 agent —— 分享式提纯的整理标准由它启发
- [TikHub](https://tikhub.io) —— 四平台社媒公开数据 API（小红书/抖音/公众号/视频号）

## License

MIT

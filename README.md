# hermes-media-suite

一台一百来块一年的云服务器 + Hermes，跑起两个真能干活的 agent：

1. **音视频转录整理**：丢一个链接/文件给它，还你一份提纯过的中文文稿（不是三句话摘要）。
   整理标准的思路来自生财有术亦仁分享的「小D」agent，在此致谢；本仓库是社区重写与升级版。
2. **四平台社媒调研**：小红书、抖音、微信公众号、微信视频号——丢链接直取内容，
   关键词跨平台搜索，挖评论区，拆对标账号。通过 TikHub 官方 API 直连，
   你自己的 key、你自己的账单，本仓库不做任何中间商。

两个 agent 拼起来是一条"收藏处理流水线"：平时随手扔进群里的链接
（公众号文章、抖音视频、小红书笔记、视频号），agent 拉回内容、转录整理、归档——
把"收藏了从没看过"变成"收藏了就有输出"。

它们跑在服务器上，不绑你的电脑。电脑关机，agent 照样干活；
在 Telegram 里发条消息就能使唤（微信接入见文末）。

## 仓库结构

```
INSTALL_PROMPT.md             一键安装提示词：复制丢给 Codex/Claude Code，替你装完整套
mcp/tikhub_xhs_mcp.py         TikHub 四平台采集 MCP（零依赖，14 个工具，全部真实调用验证过）
profiles/media-transcriber.md 转录整理 agent 的指令
profiles/social-research.md   四平台社媒调研 agent 的指令
docs/deploy-cheap-server.md   从买服务器到跑通的完整教程
```

## 快速开始

**最省事**：打开 [INSTALL_PROMPT.md](INSTALL_PROMPT.md)，把提示词填好丢给你的
Codex / Claude Code，它替你装完整套。

**想自己动手**：看 [docs/deploy-cheap-server.md](docs/deploy-cheap-server.md)，从零到跑通。

## 把账算明白

| 项目 | 花费 |
| --- | --- |
| 服务器 | 一百元上下一年（入门轻量云主机） |
| 大模型 | 自己的 key，用多少花多少（deepseek 性价比高；有 ChatGPT 会员也可接入共享额度） |
| TikHub | 按调用计费，只在用小红书调研时产生；响应带 24h 免费 cache_url。注册入口：[user.tikhub.io/register?ref=EJ7Ka9h8](https://user.tikhub.io/register?ref=EJ7Ka9h8)（带我的推荐码，不加价，介意可去掉 ref 参数） |

软件本身全部免费开源。

## 致谢

- [Hermes](https://github.com/NousResearch/hermes-agent) —— 底座 agent 框架（本仓库与 Nous Research 无关联，仅为使用者）
- 生财有术 · 亦仁的「小D」转录整理 agent —— 分享式提纯的整理标准由它启发
- [TikHub](https://tikhub.io) —— 小红书公开数据 API

## 懒得自己折腾？

这套东西自己照教程装完全没问题。但如果你想省事——

**Hermes ai共学社**（知识星球，¥199 服务费）：我帮你把 Hermes 装好、**接到微信上用**、
后续维护我管、我做好的成品 workflows / skills 持续发你（本仓库就是其中之一的开源版）。
服务器（约 ¥109/年）自购，我负责"精装修"。

加微信 **BurningChen**，备注「星球」。

## License

MIT

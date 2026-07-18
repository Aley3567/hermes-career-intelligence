# hermes-media-suite

一台一百来块一年的云服务器 + Hermes，跑起两个真能干活的 agent：

1. **音视频转录整理**：丢一个链接/文件给它，还你一份提纯过的中文文稿（不是三句话摘要）。
   整理标准的思路来自生财有术亦仁分享的「小D」agent，在此致谢；本仓库是社区重写与升级版。
2. **小红书调研**：关键词搜笔记、拉详情、挖评论区、拆对标博主——通过 TikHub 官方 API 直连，
   你自己的 key、你自己的账单，本仓库不做任何中间商。

它们跑在服务器上，不绑你的电脑。电脑关机，agent 照样干活；
在 Telegram 里发条消息就能使唤（微信接入见文末）。

## 仓库结构

```
mcp/tikhub_xhs_mcp.py        TikHub 小红书采集 MCP（零依赖，7 个工具）
profiles/media-transcriber.md 转录整理 agent 的指令
profiles/xhs-research.md      小红书调研 agent 的指令
docs/deploy-cheap-server.md   从买服务器到跑通的完整教程
```

## 快速开始

看 [docs/deploy-cheap-server.md](docs/deploy-cheap-server.md)，从零到跑通。
有 Codex / Claude Code 的话，直接把教程丢给它替你装。

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

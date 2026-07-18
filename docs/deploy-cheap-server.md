# 从一台百元服务器到跑通：完整部署教程

目标：在一台一百来块一年的入门云服务器上，跑起 Hermes + 本仓库的两个 agent
（音视频转录整理 + 小红书调研），并且让它直接在你的飞书里干活（读群里的链接、交付飞书文档）。

全程不需要你会写代码。如果你手边有 Codex 或 Claude Code，
大部分步骤可以直接把本文丢给它，让它替你执行。

## 0. 你需要准备什么

| 项目 | 说明 | 花费 |
| --- | --- | --- |
| 云服务器 | 2核2G、Debian/Ubuntu 的入门轻量云主机就够 | 一百元上下一年（各家活动价常见） |
| 大模型 API key | OpenRouter / DeepSeek 等任选，Hermes 不锁模型 | 按用量，deepseek 性价比高 |
| TikHub API key | 只有要用社媒调研 agent 才需要。注册：https://user.tikhub.io/register?ref=EJ7Ka9h8（带作者推荐码，不加价，介意可去掉 ref 参数） | 按调用次数计费 |
| 飞书自建应用 | 飞书开发者后台（open.feishu.cn/app）创建「企业自建应用」，拿到 App ID 和 App Secret——agent 靠它在飞书里干活 | 免费 |

提示：服务器选境外节点访问模型 API 和 TikHub 通常更顺；选境内节点则相反，自己权衡。

## 1. 安装 Hermes

按官方 Quickstart 一条命令安装（Linux 服务器直接支持）：

https://hermes-agent.nousresearch.com/docs

装完先跑 `hermes` 进入交互设置，填上你的模型 API key。

## 2. 拉取本仓库

```bash
git clone https://github.com/chenchen1010/hermes-media-suite.git
cd hermes-media-suite
```

## 3. 装转录工具链（转录 agent 需要）

```bash
sudo apt update && sudo apt install -y ffmpeg python3-pip
pip3 install yt-dlp
# 可选：CPU 转写兜底（短音频可用，长音频慢）
pip3 install faster-whisper
```

字幕优先策略下，大部分 B站/YouTube 素材靠 yt-dlp 拉字幕就能完成，不需要真转写。

## 4. 创建两个 profile

```bash
hermes profile create media-transcriber
hermes profile create social-research
```

把 `profiles/media-transcriber.md` 和 `profiles/social-research.md` 的内容
分别配置为对应 profile 的常驻指令（Hermes 的 profile/skill 机制见官方文档；
最省事的办法：进入对应 profile 的会话，让它读仓库里的指令文件并保存为自己的技能）。

## 5. 接上小红书采集 MCP（调研 agent 需要）

编辑 `~/.hermes/config.yaml`，加上：

```yaml
mcp_servers:
  tikhub-xhs:
    command: "python3"
    args: ["/root/hermes-media-suite/mcp/tikhub_xhs_mcp.py"]
    env:
      TIKHUB_API_KEY: "你的 TikHub key"
```

路径按你实际克隆的位置改。重启 Hermes 后，agent 就能看到 14 个跨平台采集工具（小红书/抖音/公众号/视频号）。

## 6. 接飞书（agent 的交付通道）

装 lark-cli 并绑定你的飞书自建应用：

```bash
npm install -g @larksuite/cli
lark-cli config init        # 填 App ID，App Secret 用 stdin 传入
lark-cli auth login         # Device Flow 授权
lark-cli doctor             # 验证配置健康
```

然后给两个 profile 的常驻指令补一条：整理稿优先用 lark-cli 创建飞书文档并返回链接，
发消息到指定飞书群也用 lark-cli。测试：

```text
帮我把这个视频整理成文字稿，交付成飞书文档：<粘贴一个 B 站链接>
```

## 7. 冒烟测试清单

- [ ] `hermes -p media-transcriber chat` 里丢一个带字幕的视频链接，能返回整理稿
- [ ] `hermes -p social-research chat` 里搜一个关键词，能返回笔记样本和归纳
- [ ] 整理稿能交付成飞书文档、链接可打开
- [ ] 设一个定时任务（大白话即可），到点它自己干活——关掉你自己的电脑也一样（这就是挂在服务器上的意义）

## 关于微信接入

Hermes 支持微信接入，配置并不复杂——在安装提示词里告诉你的 AI 助手
「我需要微信接入」，它会按 Hermes 的接入方式配好，之后微信里发消息就能使唤 agent。

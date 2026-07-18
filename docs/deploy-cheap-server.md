# 从一台百元服务器到跑通：完整部署教程

目标：在一台一百来块一年的入门云服务器上，跑起 Hermes + 本仓库的两个 agent
（音视频转录整理 + 小红书调研），并且在 Telegram 里就能使唤它。

全程不需要你会写代码。如果你手边有 Codex 或 Claude Code，
大部分步骤可以直接把本文丢给它，让它替你执行。

## 0. 你需要准备什么

| 项目 | 说明 | 花费 |
| --- | --- | --- |
| 云服务器 | 2核2G、Debian/Ubuntu 的入门轻量云主机就够 | 一百元上下一年（各家活动价常见） |
| 大模型 API key | OpenRouter / DeepSeek 等任选，Hermes 不锁模型 | 按用量，deepseek 性价比高 |
| TikHub API key | 只有要用小红书调研 agent 才需要。注册：https://user.tikhub.io/register?ref=EJ7Ka9h8（带作者推荐码，不加价，介意可去掉 ref 参数） | 按调用次数计费 |
| Telegram 账号 | 用来跟 agent 说话（微信接入见文末说明） | 免费 |

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
hermes profile create xhs-research
```

把 `profiles/media-transcriber.md` 和 `profiles/xhs-research.md` 的内容
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

路径按你实际克隆的位置改。重启 Hermes 后，agent 就能看到 7 个小红书工具。

## 6. 接 Telegram（随时随地使唤它）

按官方文档给 Hermes 配置 Telegram gateway。配置完成后，
手机上发一条消息试试：

```text
帮我把这个视频整理成文字稿：<粘贴一个 B 站链接>
```

```text
搜一下小红书上「手冲咖啡」相关的笔记，看看大家都在发什么角度。
```

## 7. 冒烟测试清单

- [ ] `hermes -p media-transcriber chat` 里丢一个带字幕的视频链接，能返回整理稿
- [ ] `hermes -p xhs-research chat` 里搜一个关键词，能返回笔记样本和归纳
- [ ] Telegram 里发消息，服务器上的 agent 有响应
- [ ] 关掉自己的电脑，再发一条——它还在干活（这就是挂在服务器上的意义）

## 关于微信接入

Hermes 官方支持的平台列表里没有微信。微信接入是我们在 Hermes ai共学社里
提供的服务之一（帮装好、接到微信、后续维护）。想省事的看主 README 末尾。

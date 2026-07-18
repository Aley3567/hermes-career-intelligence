# 一键安装提示词

把下面整段提示词复制出来，把【】里的信息填好，
丢给你的 Codex / Claude Code / 任何能执行命令的 AI 编程助手，它就会替你装完整套。

## 前置准备（三样必备 + 一样可选）

| 资料 | 怎么拿 |
| --- | --- |
| 云服务器 | 腾讯云轻量应用服务器 4核4G（约 ¥109/年档），拿到公网 IP、用户名（默认 ubuntu）、密码 |
| DeepSeek API Key | deepseek.com 注册 → 创建 API Key → 充 10 块钱即可用很久 |
| 飞书自建应用 | 飞书开发者后台（open.feishu.cn/app）→ 创建「企业自建应用」→ 复制 App ID 和 App Secret |
| TikHub API Key（可选） | 只在要用社媒采集时需要：https://user.tikhub.io/register?ref=EJ7Ka9h8（带作者推荐码，不加价，介意可去掉 ref 参数） |

> 安全提示：给 AI 的服务器密码建议用临时密码，装完就改；更稳的做法是配 SSH 密钥。
> 你的各种 key 只会写进服务器上的配置文件，不要让 AI 把它们写进任何会提交的代码里。

---

请帮我在一台云服务器上部署 hermes-media-suite（音视频转录整理 + 四平台社媒调研的 agent 套件），并把 agent 接进我的飞书。

服务器信息：
- IP：【你的服务器公网 IP】
- 登录：【ubuntu + 密码，或 SSH 密钥路径】
- 系统：【Debian / Ubuntu】

我的 key（没有的项跳过对应功能）：
- 大模型：【DeepSeek API key】
- 飞书自建应用：App ID【cli_ 开头】 / App Secret【】
- TikHub（社媒采集用，没有就跳过 MCP 配置）：【TikHub API key】

请按以下步骤执行，每步完成后向我报告结果：

1. SSH 登录服务器，更新系统，安装 ffmpeg、python3-pip、git、nodejs 和 npm，并 `pip3 install yt-dlp`（可选 `faster-whisper`）。
2. 按 Hermes 官方 Quickstart（https://hermes-agent.nousresearch.com/docs）安装 Hermes，配置我的 DeepSeek key。
3. 克隆 https://github.com/chenchen1010/hermes-media-suite 到服务器。
4. 创建两个 Hermes profile：`media-transcriber` 和 `social-research`，
   分别把仓库 `profiles/media-transcriber.md` 和 `profiles/social-research.md` 的内容配置为它们的常驻指令。
5. 如果我给了 TikHub key：把仓库 `mcp/tikhub_xhs_mcp.py` 配置进 `~/.hermes/config.yaml` 的
   `mcp_servers`（command: python3, args: [该文件在服务器上的绝对路径], env: TIKHUB_API_KEY），重启 Hermes 验证 20 个工具可见。
6. 安装并绑定 lark-cli（agent 操作飞书的通道）：
   - `npm install -g @larksuite/cli`
   - 用我的飞书自建应用凭证初始化：`lark-cli config init`（App Secret 通过 stdin 方式传入，不要留在 shell 历史里）
   - `lark-cli auth login` 完成授权，`lark-cli doctor` 验证配置健康
7. 给两个 profile 的常驻指令追加一条：交付整理稿时优先用 lark-cli 创建飞书文档并返回链接；
   需要发消息到我的飞书群时也用 lark-cli。然后实际测试一次：让 agent 用 lark-cli
   创建一篇标题为「部署联调测试」的飞书文档，把链接发给我确认。
8. 默认用飞书自建应用的机器人作为聊天通道：配置好后引导我和应用机器人聊天
   （也可以把机器人拉进多个群聊，不同群做不同的事）。
   微信接入：询问我【需要 / 不需要】。如果需要，按 Hermes 的微信接入方式配好，
   让我在微信里也能直接使唤它（微信里只支持一个聊天框）。
9. 跑通冒烟测试并逐项报告：
   - 丢一个带字幕的 B 站/YouTube 链接给 media-transcriber，确认能产出整理稿并交付为飞书文档
   - 让 social-research 搜一个关键词，确认能返回样本和归纳（如已配 TikHub）
   - 设一个测试定时任务（如「明早八点发我一句早安」）确认调度正常，测完删掉
10. 最后把以下信息整理给我：各 profile 怎么进入、MCP 工具清单、lark-cli 绑定状态、我的 key 分别写在了哪些配置文件里。

注意：我的所有 key 只允许写进服务器上的配置文件（如 ~/.hermes/config.yaml 和 lark-cli 的配置），
不要写进仓库目录内的任何文件，不要提交到任何 git 仓库，不要在报告里原样复述完整 key。

---

装完之后，日常使用：

```text
hermes -p media-transcriber chat    # 丢链接，出整理稿，交付飞书文档
hermes -p social-research chat      # 丢关键词或链接，出调研简报
```

配合定时任务，就是一条「收藏处理流水线」：
链接扔进飞书群 → agent 定时读取 → 拉内容、转录整理 → 成稿写回飞书。
配了微信接入的话，微信里发消息一样使唤。

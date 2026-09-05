# Cache and Cost Discipline

## Provider response cache

`BudgetedMCPClient` 包装任意 `MCPToolClient`：

1. 对 `tool_name + canonical arguments` 计算稳定 SHA-256。
2. 先查询持久化 SQLite cache。
3. 未命中才消耗 Research Budget 并调用 TikHub。
4. 只缓存成功且有数据的响应；错误与空数据不缓存。
5. 保存 TikHub `cache_url` 与过期时间，默认 TTL 24 小时。

参数 JSON 会排序，所以字典键顺序不会制造重复调用。每次真实 Provider 调用、缓存命中和估算 cost unit 都可写回 `ResearchRun`。

## Content and media fingerprints

- Content 指纹只包含平台、稳定内容 ID、Creator、标题、正文和类型。
- 点赞/评论等可变互动数与临时媒体 URL 不影响 Content 指纹。
- Media 指纹优先组合稳定 locator、ETag 和 content length；拿到文件后使用 bytes SHA-256。

## Derived-artifact ledger

`ArtifactLedger` 对 `(artifact_kind, input_fingerprint)` 做唯一约束，用于避免重复：

- `transcript + media_hash`
- `embedding + transcript_hash`
- `claim_extraction + content_hash`

首次 worker 获得 reservation；重复 worker 不再执行昂贵任务。部署阶段会增加 pending reservation 的超时恢复。

## Default budget

单次 Research Run 默认最多 10 个付费 Provider 调用。先搜一页、评估方向，再显式扩样。不同 TikHub 工具可配置不同 cost unit，但不得用“点赞高”替代证据充分度。

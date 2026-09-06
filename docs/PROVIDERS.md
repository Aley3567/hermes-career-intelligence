# Social Provider Contract

Career Intelligence 不直接依赖 TikHub 的原始 JSON。每个平台 Adapter 负责把搜索、内容、Creator 和评论归一化为稳定 DTO，Research Engine 只读取 DTO。

## Xiaohongshu v1 boundary

`TikHubXHSProvider` 通过依赖注入的 `MCPToolClient` 调用 upstream 工具：

| Provider 方法 | MCP 工具 |
| --- | --- |
| `search_notes` | `xhs_search_notes` |
| `get_note` | `xhs_get_note_detail` |
| `get_creator` | `xhs_get_user_info` |
| `search_creators` | `xhs_search_users` |
| `get_creator_notes` | `xhs_get_user_posted_notes` |
| `get_comments` | `xhs_get_note_comments` |

Adapter 只返回业务必需字段，不长期保留整份原始响应。`request_id` 和 `cache_url` 作为分页元数据保留；Provider 错误转换为不包含原始响应 body 的 `ProviderError`。

## Pagination and cost

- 首次搜索默认 `page=1`，不自动扩页。
- 后续页沿用 TikHub 返回的 `search_id` 与 `search_session_id`。
- `time_filter` 用于限制研究时间窗。
- `cache_url` 进入下一阶段缓存层；Adapter 本身不擅自重复调用。
- `get_note(note_type="auto")` 可能触发两次付费请求，已知类型时必须明确传入。

TikHub 官方文档显示 App V2 搜索需要在翻页时沿用首次响应的搜索标识，因此这些参数以 additive 方式补入现有 MCP，不重写原工具。

参考：[TikHub App V2 Search Notes](https://docs.tikhub.io/420136398e0)、[TikHub App V2 Note Detail](https://docs.tikhub.io/420136391e0)。

# GitHub Issues Backlog

Fork 可写后按以下顺序创建；每项都能独立验收。

1. **[P0] Establish fork baseline and upstream remote**  
   验收：`origin` 指向 `Aley3567/hermes-career-intelligence`，`upstream` 指向原仓库，记录基线 commit。
2. **[P1] Add domain models and evidence invariants**  
   验收：User/Profile 分离；Evidence 时间戳成对；未知字段被拒绝。
3. **[P1] Persist claims, evidence, profiles and results in SQLite**  
   验收：Profile round-trip；Claim 可反查 Evidence；重启后数据存在。
4. **[P1] Ship deterministic offline acceptance demo**  
   验收：输出 Consensus、Disagreement、Emerging Signal、Gap 与 30 天动作。
5. **[P2] Implement TikHub XHS provider adapter and normalized DTOs**  
   验收：搜索、笔记、Creator、评论均可用 fixture 重放；不泄漏原始 secret。
6. **[P2] Add cache and research-call budget**  
   验收：相同内容不重复抓取，24h cache_url 优先，调用次数进入 ResearchRun。
7. **[P3] Implement content and creator ranking**  
   验收：粉丝数不主导；高营销比例降权；重复内容被抑制。
8. **[P3] Implement claim clustering and disagreement detection**  
   验收：支持/反对证据均保留，Claim 可回溯原文。
9. **[P4] Expose the 10-tool Career MCP surface**  
   验收：外部看不到 SQL、ffmpeg、embedding 等内部工具。
10. **[P4] Integrate Hermes profile, skills and worker orchestration**  
    验收：核心问题可从 Hermes 触发并返回合法 ResearchPack。
11. **[P5] Add secure long-running deployment**  
    验收：健康检查、重启恢复、日志脱敏、`.env.example` 完整。
12. **[P6] Run the real XHS career pilot**  
    验收：真实来源 ResearchPack；每个重要 Claim 有 Evidence；列明采样限制。


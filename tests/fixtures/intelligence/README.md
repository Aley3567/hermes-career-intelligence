# Intelligence Golden Fixtures

本目录只存虚构、确定性、可离线运行的 Stage 4 测试样本。默认 CI 不读取真实小红书内容、不需要 TikHub Key，也不导入 live provider client。

每个 fixture case 应明确：输入角色、要验证的风险、最小期望结果。

| Case | 目的 | 核心断言 |
| --- | --- | --- |
| `first_hand_high_signal` | 第一手高质量内容 | 高于泛泛总结和营销内容 |
| `marketing_heavy` | 营销惩罚 | 即使互动量高也不能进入 Top Tier |
| `duplicate_repost` | 去重 | 重复内容/转载不增加独立共识来源数 |
| `low_quality_popular` | 防止 popularity bias | follower/engagement 不能压过可信度与信息密度 |
| `supporting_independent` | 共识 | 两个独立 Creator 支持同一 Claim，可形成 consensus candidate |
| `explicit_conflict` | 分歧 | 两侧 Evidence 均保留，不能多数票覆盖反方 |
| `emerging_signal` | 新兴趋势 | 近期频率上升且历史基线低 |
| `old_popular_signal` | 新兴信号反例 | 长期高频观点不能被误判为 emerging |
| `timestamped_video` | 视频证据 | Claim → Evidence → transcript start/end 可逆追踪 |
| `user_gap` | Gap Analysis | 外部 Claim 只用于生成 gap，不修改 UserProfile 原始事实 |

规则：

1. 所有人名、公司名、链接和平台 ID 使用虚构值。
2. 所有时间固定，不使用 `datetime.now()`。
3. 每个排序 fixture 必须能断言 `ScoreBreakdown`，不仅断言最终名次。
4. duplicate case 必须同时覆盖内容 hash 与独立 Creator 计数。
5. conflict case 必须有明确 supporting/counter Evidence。
6. fixture 中的“预期结论”只用于测试算法行为，不代表真实求职市场判断。
7. 真实固定样本若未来加入，放在独立 opt-in 路径，并经过脱敏与授权检查。

`manifest.json` 是 Stage 4 实现前冻结的测试矩阵；实现 PR 不应为了让测试通过而静默改变 case 语义。若确需修改，应在 PR 中解释算法或领域假设变化。

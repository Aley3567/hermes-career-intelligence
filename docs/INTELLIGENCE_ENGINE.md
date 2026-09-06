# Stage 4 Intelligence Engine Contract

Stage 4 的目标不是“让模型多总结几段”，而是把已归一化的社媒内容转换成可追踪、可复现、可解释的求职情报。

## 1. 输入边界

Intelligence Engine 只消费项目自有的领域对象，不接收 TikHub 原始 DTO、HTTP response 或平台 SDK 对象。

输入来源：

- `NormalizedContent` / `NormalizedComment` / `NormalizedCreator`
- `Transcript` / `Evidence`（视频证据必须保留时间戳）
- `UserProfile`
- 显式 `as_of` 时间，用于可复现的 recency 计算

Provider 负责采集和归一化；Intelligence Engine 不直接调用 TikHub。

## 2. 输出边界

最终仍输出现有 `ResearchPack`，其中重要结论必须能反向定位到 `Evidence`。

强制不变量：

1. 每个 `Claim` 至少有一个 Evidence ID。
2. supporting evidence 与 counter evidence 分开保存，不允许为了形成“共识”而丢掉反例。
3. 视频 Evidence 必须保留 transcript start/end 时间戳。
4. Mock、fixture、真实平台样本必须带清晰来源标记，禁止混写成真实结论。
5. UserProfile 与外部 Claim/Evidence 始终分区；外部观点不能直接覆盖用户事实。
6. 无法形成足够证据时返回 limitation/uncertainty，而不是补全结论。

## 3. 流水线顺序

```text
Normalized Provider Data
        ↓
Candidate Selection / Ranking
        ↓
Evidence Extraction
        ↓
Claim Proposal + Validation
        ↓
Claim Normalization / Duplicate Detection
        ↓
Clustering
        ↓
Consensus / Disagreement / Emerging Signal
        ↓
User Gap Analysis
        ↓
ResearchPack
```

顺序有意把 Ranking 放在昂贵的 Extraction/ASR 前面，以控制 TikHub、转录和模型调用成本。

## 4. Ranking Contract

第一版必须可解释且确定性运行。每个内容/Creator 的排名结果必须返回 feature contribution，而不仅是一个 opaque score。

### 正向特征

- `relevance`：与当前 research question 的相关度
- `first_hand_experience`：第一手招聘/面试/项目经验程度
- `signal_density`：单位内容中的可验证信息密度
- `credibility`：身份与陈述可信度信号
- `recency`：相对显式 `as_of` 的时间衰减
- `useful_content_ratio`：历史有用内容占比

### 惩罚特征

- `marketing_penalty`
- `duplicate_penalty`

### 限制

- follower count 不得直接主导 score；只能作为辅助元数据或受严格上限的 tie-break signal。
- engagement 不得替代 relevance/credibility。
- 所有时间相关分数必须使用注入的 `as_of`，测试不得依赖当前系统时间。
- 总分及各 feature contribution 必须能被 fixture 精确断言。

建议输出结构：

```text
ScoreBreakdown
  relevance
  first_hand_experience
  signal_density
  credibility
  recency
  useful_content_ratio
  marketing_penalty
  duplicate_penalty
  total
```

## 5. Extraction Contract

Claim Extraction 可以使用 LLM，但 LLM 输出只是 proposal，不是事实。

每条 proposal 至少包含：

- `claim_text`
- `normalized_claim`
- `topic`
- `stance`（supports / counters / context）
- `evidence_id`
- 对视频：timestamp range

写入正式 Claim 前必须通过领域模型验证；找不到原始 Evidence 的 proposal 必须丢弃。

禁止：

- 从摘要反推不存在的原文证据
- 合并不同来源后生成一个无法追溯到单个来源的“综合证据”
- 在 extraction 阶段根据用户偏好修改外部观点

## 6. Duplicate / Clustering Contract

重复处理分两层：

1. 内容级 duplicate：转载、重复抓取、相同稳定 ID/内容 hash。
2. Claim 级 semantic cluster：措辞不同但表达相近观点。

Cluster 只能建立关联，不能删除来源特有措辞和 Evidence。

Consensus 至少考虑：

- 独立 Creator 数，而非单个 Creator 的重复发帖数
- source quality
- recency
- 跨来源支持

Disagreement 必须保存双方 Evidence，不能用多数票覆盖少数观点。

Emerging Signal 必须同时表现出“近期频率上升”和“历史基线较低”；只有高热度但长期存在的观点不算新兴信号。

## 7. ASR Selection Contract

视频是否转录由 expected information value / cost 决定，而不是“只要是视频就转录”。

优先转录：

- 高排名但正文信息不足
- 字幕/标题暗示存在招聘标准、面试复盘、项目细节
- 可能提供关键 counter evidence

已有 transcript/content hash 命中时必须复用 Stage 3 的 artifact ledger。

## 8. Stage 4 实现顺序

1. **4A Ranking**：ScoreBreakdown、内容/Creator 排名、ASR value/cost 选择。
2. **4B Extraction**：Evidence-first Claim proposal + validation。
3. **4C Clustering & Signals**：duplicate、cluster、consensus、disagreement、emerging。
4. **4D Retrieval**：exact/metadata + semantic retrieval，返回 compact ResearchPack/Evidence references。

4A 完成前不扩大采样；4B 完成前不把模型摘要当 Claim；4C 完成前不声称存在真实共识/趋势。

## 9. Stage 4 Definition of Done

- Golden fixtures 可完全离线复现。
- 排名结果及 feature contributions 可断言。
- 每个重要 Claim 可追踪到原始 Evidence。
- counter evidence 不丢失。
- duplicate Creator/转载不会虚增 consensus。
- Emerging Signal 有历史基线比较。
- retrieval 不混合 UserProfile namespace 与 external evidence namespace。
- 固定真实样本回归测试仅作为 opt-in；默认 CI 不依赖 TikHub、网络或私密凭据。

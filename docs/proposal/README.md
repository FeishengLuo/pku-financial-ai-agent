# Claim2Value 项目书（Proposal）

> 北大金融 AI 智能体大赛参赛作品 · 证据可追溯的行业研究 Agent（机器人减速器行业）
> 状态：**初稿进行中**。第 5 章"商业潜力"为完整初稿（本文集分值权重最高章节）；
> 其余章节为骨架，素材索引已标注，待按排期填充。
> 所有第 5 章数字均可回溯至 `research_materials/notes/commercial/C1–C8` 笔记（含页码/链接/日期）。

## 章节结构

| 章 | 文件 | 状态 | 说明 |
|---|---|---|---|
| 1 项目概述 | `01_overview.md` | 骨架 | 一句话定位、痛点、方案总览、团队 |
| 2 技术方案 | `02_technical.md` | 骨架 | 证据链/验证器/财务影响链路（代码已就绪：src/ + tests/ 129 passed） |
| 3 数据与证据 | `03_data_evidence.md` | 骨架 | 18 份披露/研报 PDF、19 条 Claim、5 条已核验回填（PR #11） |
| 4 演示与复现 | `04_demo.md` | 骨架 | 本地 workflow、五要素 Demo、复现步骤 |
| **5 商业潜力** | **`05_business_case.md`** | **完整初稿** | TAM/SAM/SOM、竞争格局、估值对照、竞品定价、商业模式、风险 |
| 6 实施计划 | `06_roadmap.md` | 骨架 | 三周排期、分工、里程碑 |
| 7 财务与成本 | `07_financials.md` | 骨架 | 项目自身成本（LLM API 成本结构见 §5.8） |
| 8 风险与合规 | `08_risk_compliance.md` | 骨架 | 数据合规、免责声明、模型边界 |

## 素材地图（写章节时从这里取数）

| 章节 | 主要素材 |
|---|---|
| §1–§2 | `src/`（workflow、verifier、claim_bank_writer）、`tests/`、`benchmarks/pipeline_report.md` |
| §3 | `data/processed/claim_bank_filled.json`、`data/raw/`（18 PDF + meta）、`SYNC_LOG.md` |
| **§5** | `research_materials/notes/commercial/` 全部 7 份笔记（C1–C8） |
| §6–§8 | 本目录骨架 + `TODO.md` |

## 写作纪律（全队遵守）

1. 每个数字必须带出处：本地素材标"文件名 + 页码"，网络素材标"机构 + 日期 + 链接"。
2. 未取得 / 低可信度数据按 C1–C8 笔记中的原标注转写，不得升级为确定表述。
3. 口径打架时并列展示（例：GGII vs 高盛出货量），不擅自取舍。
4. 财务模型输出为**原型情景**（`model_status = prototype_scenario_not_investment_recommendation`），任何引用须带此限定。

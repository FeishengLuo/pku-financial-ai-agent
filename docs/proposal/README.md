# Claim2Value 项目书（Proposal）

> 北大金融 AI 智能体大赛参赛作品 · 证据可追溯的行业研究 Agent（机器人减速器行业）
> 状态：**初稿完成**。第 5 章"商业潜力"为完整初稿（本文集分值权重最高章节），
> 第 1–4、6–8 章正文已按骨架展开（PR #14）；各章数字与第 5 章同源同值。
> 所有第 5 章数字均可回溯至 `research_materials/notes/commercial/C1–C8` 笔记（含页码/链接/日期）。

## 章节结构

| 章 | 文件 | 状态 | 说明 |
|---|---|---|---|
| 1 项目概述 | `01_overview.md` | 初稿 | 一句话定位、痛点、方案总览、商业一页 |
| 2 问题定义与需求分析 | `02_problem.md` | 初稿 | 用户画像、工作流痛点、四大缺口（各配实例）、紧迫性 |
| 3 产品方案与技术架构 | `03_product.md` | 初稿 | 已建成系统架构（代码可验证）、核心机制、140 测试质量证据 |
| 4 实证案例：绿的谐波 | `04_case_study.md` | 初稿（重心） | 证据链全流程演示、双预期差、三情景估值、隐含预期反推 |
| **5 商业潜力** | **`05_business_case.md`** | **完整初稿** | TAM/SAM/SOM、竞争格局、估值对照、竞品定价、商业模式、风险 |
| 6 实施路线图与里程碑 | `06_roadmap.md` | 初稿 | 三阶段路线（与 §5.7.4 对齐）、资源需求、外部风险 |
| 7 团队与分工 | `07_team.md` | 初稿 | 能力画像、已交付物对照（PR 清单）、协作工作流 |
| 8 合规、伦理与社会价值 | `08_compliance.md` | 初稿 | 证据对照≠投资建议、数据合规、可审计设计即伦理实践 |

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

# 第 3 章 产品方案与技术架构（待写）

## 本章任务

描述产品形态与系统架构。工程底座大部分已在 P1 阶段实现并开源，
本章是"向评委展示已建成系统"而非"设想"。

## 建议结构

- 3.1 产品形态：证据链分析智能体（对话式 + Claim Bank + 报告生成）
- 3.2 系统架构：数据采集 → pipeline（`src/data_tools/`）→ Claim Bank
  （`claim_bank_writer`）→ 报告组装
- 3.3 核心机制：claim 溯源、置信度分级、推理留痕、多口径并列
- 3.4 关键实现与仓库指针（给出主要模块文件路径，评委可验证）

## 素材指针

- 仓库代码：`src/`、`tests/`（129 个回归测试通过）
- `research_materials/notes/` 下的 Claim Bank 与 pipeline 笔记
- 三情景估值原型：`data/processed/green_harmonic_model_results.json`

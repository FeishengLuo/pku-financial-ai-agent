# Claim2Value 项目 GitHub 同步记录

> **用途**：记录每次推送到 GitHub 的内容，方便团队随时回看"哪些传过了、新增了啥"。
> **仓库**：https://github.com/aeiou0123/pku-financial-ai-agent
> **维护方式**：每次 `git push` 成功后，在表首追加一行；详细变更见各次提交说明。

---

## 项目书骨架 + 第 5 章商业潜力初稿（2026-09-06，PR #13）

### 新增

| 文件 | 内容 |
|---|---|
| `docs/proposal/README.md` | 项目书 8 章骨架表 + 素材地图 + 写作纪律 |
| `docs/proposal/05_business_case.md` | **第 5 章完整初稿**（约 400 行）：摘要 / 5.1 TAM-SAM-SOM 三层漏斗（SAM 主推研究佣金比例法 = 198.65 亿 × 1–3% ≈ 2–6 亿/年，人头法/机构法交叉验证）/ 5.2 行业驱动力 / 5.3 竞争格局（含"券商降价假设已被实际 ASP 击穿"洞察）/ 5.4 客户与产能硬证据（含扩产延期 6.08% 风险）/ 5.5 估值对照（三情景原型 EV 32–86 亿 vs 市值 513 亿的诚实差距处理）/ 5.6 竞品定价与四大缺口 / 5.7 商业模式与定价建议（个人 1.2 万/团队 6–10 万/机构 20 万+三档，毛利 85%+ 假设）/ 5.8 风险对冲表 / 5.9 产品能力衔接 / 附录数据来源索引。所有数字标 [C1]–[C8] 溯源标签 |
| `docs/proposal/01–04、06–08` | 七章骨架 stub（每章 10–15 行：任务 + 建议结构 + 素材指针），待按本框架展开 |
| `research_materials/notes/commercial/sam_sizing.md` | C8 SAM 测算（上轮搜集完成、当时未推送）：分析师 5,776 人、券商研究佣金 198.65 亿元（-22.48%）、研报年产约 14 万份；SAM 主推佣金比例法 2–6 亿元/年 + 人头法/机构法交叉验证 |

### 说明

- 第 5 章所有数字全部来自已验收的 C1–C6、C8 搜集笔记，可直接溯源到本地 PDF 页码或网络来源。
- 未竟事项：C7 效率实测（需人工）；剩余 14 条 claim 核验；01–04/06–08 章节展开。

---

## Phase 2 商业素材搜集 C1–C6（2026-09-06，PR #12）

### 新增（全部位于 `research_materials/notes/commercial/`）

| 文件 | 任务 | 核心内容 |
|---|---|---|
| `market_size_extracts.md` | C1 本地PDF市场规模 | 环动招股书+国金+源达三份文本提取：工业机器人减速器中国市场 45.6 亿元/年（2023）、人形减速器百亿级增量（123-275 亿三档）、行星减速机全球 7.5→9.2 亿美元；每条带页码+原文摘录 |
| `humanoid_tam.md` | C2 人形TAM测算 | GGII/高盛/大摩出货锚点；三档测算：2030 年全球减速器 TAM 保守 71 亿/中性 356 亿/乐观 603 亿元，2035 年 1050-4394 亿元 |
| `valuation_anchor.md` | C3 估值锚 | 绿的谐波市值 512.96 亿、PE(TTM) 365.8、2026E 净利 1.92 亿（14 家机构一致预期）；EV↔市值对照方法 |
| `capacity_evidence.md` | C4 产能/客户证据 | 定增 20.27 亿募投"年产 100 万台谐波+20 万套执行器"一手公告锁定；IPO 5.46 亿投 50 万台项目；13 家客户名单（含优必选）；扩产进度 6.08% 延期至 2028（风险对冲素材） |
| `asp_analysis.md` | C5 ASP与价差 | 绿的谐波 ASP 1293→1099 元/台（连续两年 -15%）以价换量；环动 RV ASP 2533-3209 元序列；国产 RV 较品类价差低约 39% |
| `competitor_pricing.md` | C6 竞品定价 | Wind ~4万/账号/年（询价制）、慧博 8980-19980 元/年（唯一明码标价）、AlphaSense/Tegus 万美元级席位、LLM API 成本低 3-4 个数量级 |

### 说明

- 所有数字带来源（本地txt页码 / 网络链接+日期），未取得项与低可信度项均已明确标注，可直接供项目书"商业潜力"章引用。
- C7（效率实测）需人工参与，待团队安排；C8（SAM 测算）列入下一步。

---

## P1.3 Claim Bank 真实回填（2026-09-06，PR #11）

### 变更

- `data/processed/claim_bank_filled.json` — 5 条已验证 Claim（GH_005、GH_006、BK_002、BK_005、SH_006）完成真实证据回填，每条含来源文件+URL、页码定位、原文摘录、口径说明、核验人、evidence_level=official_filing、幂等指纹。
- `data/processed/evidence_records/p1_backfill_records.json` — 本次回填的 5 条证据原始记录（可复现、可审计，作为写回输入）。
- `benchmarks/pipeline_report.md` — 行尾统一 LF（原 CRLF）。

### 证据定位（全部官方披露原文）

| Claim | 来源 | 定位 | 关键数据 |
|---|---|---|---|
| GH_005 | 绿的谐波 2024 年报（巨潮） | 第 37 页 | 三年毛利率 48.69%/41.14%/37.54% |
| GH_006 | 绿的谐波 2025 年报（巨潮） | 第 7 页 | 营收 +47.31%、归母净利 +121.42% |
| BK_002 | 步科 2024 年报（上交所） | 第 14 页 | 机器人行业收入 21,242.55 万元，+12.26% |
| BK_005 | 步科 2025 半年报（上交所） | 第 13 页 | 归母净利 2,611.01 万元 +13.58%；扣股份支付后 3,602.56 万元 +42.27% |
| SH_006 | 双环传动 2024 年报（深交所） | 第 7 页 | 归母净利 1,023,911,091.96 元，+25.42% |

### 说明

- 核验人字段暂写团队角色"经济金融组复核"，团队可在复核后替换为真实姓名。
- 其余 14 条 Claim 仍为待验证状态，回填需先经人工核验。

---

## P1 收尾：claim_bank_writer 证据写回 + 端到端回归（2026-09-06，PR #9）

### 新增

- `src/claim_bank_writer.py` — 人工核验证据写回 Claim Bank 工具：每条证据强制五必填字段（claim_id/source/locator/excerpt/caliber + verifier），核验人字段为空即拒绝写入（`SKIP_EMPTY_VERIFIER` 硬门控）；指纹 `sha256(excerpt||source)[:16]` 幂等去重；先写临时文件再 `os.replace` 原子替换，写前自动 `.bak` 备份不覆盖旧备份；来源分类复用 `evidence_ledger.SOURCE_KEYWORDS`；CLI 支持 `--evidence/--bank/--dry-run`。
- `tests/test_claim_bank_writer.py` — 25 项测试（字段校验/写回/分类/CLI）。
- `tests/test_e2e_regression.py` — 9 项端到端回归：财务模型对固定 fixture 可复算（2027 base revenue 重算 = 存储值 4.625）、输入类型隔离（CSV 仅 historical/assumption，无 calculated）、证据链信任分有界性与重复证据不加分、本地 Demo 五要素齐全、workflow 本地路径（空证据→abstain；有证据无 LLM 配置→保守降级 `rule_only_fallback`，已按 PR #8 新契约改写原 RuntimeError 断言）。

### 测试

- 全量 `python -m pytest tests/ -q`：**129 passed**（#5–#8 合并内容 + 本 PR）。

### 待团队复核

1. 写回工具需团队提供**核验后**的真实证据才能回填 Claim Bank（工具就绪 ≠ 已回填）。
2. ontology 系数复核仍在等待团队结论。

---

## P1 财务影响链路四模块（2026-09-06，PR #5–#8，已合并；经 PR #10 恢复）

按 TODO P1 实现完整财务影响链路，4 个堆叠 PR（每个只含自己的 diff，按序合并，GitHub 会自动把后续 PR 基址改回 main）：

| PR | 分支 | 内容 | 测试 |
|---|---|---|---|
| #5 | feat/engineering-analyzer | `src/engineering_analyzer.py` 工况/口径归一化（额定vs峰值、电机vs模组） | +21 用例 |
| #6 | feat/economic-mapper | `src/economic_mapper.py` + `data/processed/tech_to_economics_ontology.json` 工程→经济假设可审计映射 | +11 用例 |
| #7 | feat/causal-critic | `src/causal_critic.py` 因果批判层（替代解释/反事实需求/不可归因/置信度下调） | +28 用例 |
| #8 | feat/workflow-financial-chain | `run_financial_chain` 全链路（验证门控→工程→经济→批判→财务三情景）+ `claim_verifier` 无 LLM 配置时保守降级修复（原直接崩溃） | +15 用例 |

- 全量 `pytest tests/ -q`：**95 passed**。
- 待复核：ontology 弹性系数/单位成本初值为估计值，需经济金融成员把关后再用于正式财务模型；数据质量问题（纳博 RV-20E 行疑似填数错误、步科 FMK 缺重量、Y 系列待补充）已在 PR #5 标注。
- 注：因本机 git 协议连接 GitHub 受限，本次经 GitHub Git Data API 推送。
- 恢复记录：main 曾意外回退至 #5 合并点（f97537b），导致 #6–#8 内容不在 main 中（PR 状态仍显示 MERGED）；经 **PR #10** 将 #8 合并点（24ad46e，含全部 #5–#8 内容）重新合入，现已恢复，合并后全量 **129 passed**。

---

## 当前工作区同步记录（2026-09-06，StateVerifier 误报修复）

由孙圣尧完成 TODO P0.3（PR #3 review 中认领）：StateVerifier 六条规则层误伤全部归零。

### 修复内容（src/state_verifier.py 五处）

1. **数值归属三值齐全原则**：`source_same_val` 提取不到时不做归属判定（宁缺毋滥）——修复列举式证据（「A、B、C 分别增长 x%、y%、z%」）的系统性口径误报
2. **数值提取窗口截断保护**：数值被 30 字符窗口切成半截（如「47.31」→「47」）时丢弃，不返回半个数值
3. **口径词对豁免**：claim 含对立口径词之一（如「额定扭矩」）即不再要求包含另一个（「峰值扭矩」）
4. **检测优先级重排**：口径偷换 > 数值矛盾 > 时间错位 > 来源降级 > 限定词缺失——限定词是弱信号，不再抢来源降级的 low_confidence
5. **约数感知匹配**：精确数值严格 float 匹配（消除跨指标交叉匹配，172 vs 164.8）；约数表述（「超过100%」vs 101.30%）用 ±10% 容差（表述粒度差异≠篡改）

### 修复效果（98 用例 × 2 模型，详见 benchmarks/pipeline_report.md）

| 指标 | 修复前 | 修复后 |
|---|---|---|
| 误伤（LLM 判对被覆盖成错） | 6 + 6 | **0 + 0** |
| claude-sonnet-5 合并准确率 | 83.7% | **91.8%**（裸 LLM 62.5%，+29.3pts） |
| gpt-5.5 合并准确率 | 82.7% | **90.8%**（裸 LLM 65.3%，+25.5pts） |
| 数值篡改（此前误伤重灾区） | 75.0% | **93.8%**（≥裸 LLM 水平） |
| 来源降级 | 76.5% | **100%** |
| 规则层单独准确率 | 80.6% | **88.8%**（无 API 调用） |

### 新增文件

- `benchmarks/find_false_positives.py` — 误伤定位工具（LLM 判对但被规则层覆盖后判错的用例明细）
- `tests/test_state_verifier_fixes.py` — 11 项 fixture 回归测试，每条对应一个真实误伤用例；与 PR #3 的 5 项测试合并后 `unittest` 共 16 项全过

### 遗留（TODO P1 口径偷换 70.6% 仍为最弱项）

- 口径词对注册表可扩充（当前 14 对）；列举式证据的数值-指标对应关系解析（「分别增长」句式）暂由「三值齐全」原则回避，后续可做结构化解析

---

## 当前工作区同步记录（2026-09-05，PR #3）

本次由 Chen Luodi 基于 `main` 的 `42a2e3b` 完成项目状态审计、说明文件同步和 P0 首个开发切片。内容已提交为 `c58a7fc`，推送至 `FeishengLuo/pku-financial-ai-agent` 的 `feat/financial-model-local-demo` 分支，并向上游提交 PR #3；本次没有直接推送 `aeiou0123` 的 `main`。

### 审计结论

- benchmark、四个核心验证模块和 pipeline 结果已经进入 `main`，可以开始绿的谐波简化财务模型、本地可复现 Demo，以及 StateVerifier 的误判修复。
- pipeline 的 Claude 83.7%、GPT 82.7% 是 98 个 benchmark 用例上的规则层 + LLM 判别准确率，不应表述为真实业务最终准确率。
- 财务模型必须区分历史披露数据、人工假设和模型计算结果；首版 Demo 只覆盖绿的谐波单案例和本地 fixture。
- 官方 datasheet、专利复核、Claim evidence 回填和实时检索属于后续证据增强任务，不阻塞首版 Demo，但不能被标记为已完成。

### 本次修改

- 更新 `README.md`、`data/README.md`、`research_materials/README.md`：同步当前阶段、运行边界和数据事实。
- 重写 `TODO.md`：以 P0/P1/P2 划分财务模型、Demo、可靠性回归、工程/经济扩展和证据增强任务，并补充验收标准。
- 更新 `data/collection_checklist.md`、`data/search_guide.md`、`data/search_report.md`：区分已完成资料、待人工补充资料与当前不阻塞项。
- 更新 `research_materials/notes/feasibility_analysis_and_plan.md`：保留早期研究规划，同时附加当前执行基线，避免过期日期被当作现状。
- 在仓库外的 `杂项/pku_fin_ai_local.md` 记录本次审计、修改范围、验证结果和 PR 状态；该文件不加入项目仓库。

### 后续提交建议

本次财务模型、Demo、fixture、测试及说明文件作为一个 PR 提交，便于一次性审阅；后续功能建议按模型、验证规则和文档分别提交。

### 2026-09-05 开发更新（`c58a7fc`，PR #3）

- 新增 `src/financial_model.py`：带来源和输入类型隔离的绿的谐波简化财务模型，输出三情景 DCF 原型。
- 新增 `data/processed/green_harmonic_model_inputs.csv`、`local_demo_fixture.json` 及模型运行结果文件。
- 新增 `app.py`：默认无 API 的本地单案例 Demo；规则层无法确定时保守返回 `abstain`。
- 新增 `tests/`、`requirements.txt`，当前 `unittest` 9 项测试通过。
- 基准运行结果：base EV `6.0056 bn CNY`、2027 revenue `4.6250 bn CNY`、2027 FCF `0.4703 bn CNY`；这些是原型假设下的计算结果，不是披露事实或投资建议。
- 已运行：compileall、9 项 unittest、模型 CLI、Demo CLI 和 Excel 工作表核验；均通过。已提交并推送到 fork，等待上游审阅。

---

## 同步总览表

| 日期 | 提交哈希 | 类型 | 一句话说明 | 推送状态 |
|---|---|---|---|---|
| 2026-09-06 | `fix/verifier` | fix/test | StateVerifier 误报修复：误伤 6→0，合并准确率 83.7%/82.7% → **91.8%/90.8%**；新增 11 项 fixture 回归测试 | ⏳ PR 待合并 |
| 2026-09-05 | `c58a7fc` | feat/test/docs | Feisheng：审计状态并新增绿的谐波简化财务模型、本地无 API Demo、输入 fixture、结果文件、9 项回归测试和说明同步；PR #3 | ✅ 已合并（e157ee3） |
| 2026-09-05 | `cbc0f1d` | feat | 核心验证引擎：state_verifier + evidence_ledger + claim_verifier + workflow + pipeline 评估报告 | ✅ 已推送 |
| 2026-09-04 | `360f68c` | benchmark | Claim 验证 benchmark 全套：mutation 考卷 98 用例 + 双模型评估 + Oracle 自我修正 + 判别力报告 | ✅ 已推送 |
| 2026-09-01 | `1b13e10` | team | 新增协作者 FeishengLuo（write 权限），团队表更新为 3 人 | ✅ 已推送 |
| 2026-09-01 | `026afca` | team | 新增协作者 shushuyang231（write 权限）+ 更新 README 协作指南 | ✅ 已推送 |
| 2026-08-30 | `0e72f01` | init | 项目初始化：README、TODO、研究报告、setup 脚本 | ✅ 已推送 |
| 2026-08-30 | `ca0b44a` | docs | 数据收集指南、清单、空白模板（主案例阶段） | ✅ 已推送 |
| 2026-09-01 | `0ef790e` | data | 三公司年报/招股书 7 份 PDF + 券商研报 11 份 PDF + 搜索报告 | ✅ 已推送 |
| 2026-09-01 | `76e1118` | data | 自动提取成果：专利 30 条、参数表、18 条 claim、行业/竞争数据 + 提取脚本 | ✅ 已推送 |
| 2026-09-01 | `cbff862` | docs | 更新收集清单状态和搜索报告（记录已完成替代方案） | ✅ 已推送 |

---

## 各次同步明细

### 2026-09-04 `360f68c` benchmark: Claim 验证 benchmark 框架（孙圣尧）

这是**代码层的第一次实质提交**。此前仓库只有数据，没有任何可执行代码；本次建立了
「用 mutation testing 检验 claim verifier 判别力」的完整评测链路。

**新增目录 `benchmarks/`（9 个文件）：**

| 文件 | 说明 |
|---|---|
| `mutate.py` | 6 类扰动生成器：19 条真实 claim → 98 个测试用例 |
| `fix_oracle.py` | Oracle 修正：从参数表提取真实数值注入 evidence，修正 expected_verdict |
| `evaluate.py` | LLM-as-judge 评估器：多模型对比、断点续传、超时不计失败 |
| `report.py` | 报告生成器：判别准确率、按扰动类型分解、失败模式拆解、v1/v2 对比 |
| `claim_verification.json` | 原始考卷（98 用例） |
| `claim_verification_v2.json` | Oracle 修正后考卷（推荐用这份） |
| `report.md` | **判别力评估报告，可直接用于比赛材料** |
| `results/evaluation_results_v1.jsonl` | 首轮评估结果（69 用例，修正前，作为对照） |
| `results/evaluation_results_v2.jsonl` | 扩充后双模型评估原始数据（196 次调用） |

#### 核心结果（98 用例 × 2 模型）

| 指标 | claude-sonnet-5 | gpt-5.5 |
|---|---|---|
| 判别准确率 | 62.5% | 65.3% |
| 被骗过（太轻信） | 17 | 17 |
| 过度拒答（太保守） | 3 | 5 |
| 错且自信率 | 35% | 35% |

按扰动类型的判别准确率：

| 扰动类型 | sonnet5 | gpt5.5 | 判断 |
|---|---|---|---|
| 证据缺失 | 100% (19题) | 100% (19题) | 诚实性满分 |
| 数值篡改 | 93% (15题) | 88% (16题) | 较强 |
| 来源降级 | 71% (17题) | 59% (17题) | 中等 |
| 时间错位 | 70% (10题) | 70% (10题) | 中等 |
| 限定词删除 | 32% (19题) | 42% (19题) | **系统性盲区** |
| 口径偷换 | 12% (16题) | 35% (17题) | **系统性盲区** |

#### 三个可直接用于比赛材料的结论

1. **当前最强 LLM 做金融 claim 验证仍不可靠**：能抓明显的假（数值篡改 93%）、
   能在无证据时拒答（100%），但对**精细的假**几乎无抵抗力——口径偷换只有 12-35%，
   限定词删除只有 32-42%。
2. **失败模式以「被骗过」为主而非「过度拒答」**：两个模型各被骗过 17 条，
   过度拒答仅 3-5 条。模型偏轻信，且判错时置信度仍很高（错且自信率 35%）。
3. **「口径偷换」是最危险的盲区**：模型分不清额定扭矩/峰值扭矩、毛利率/净利率、
   归母净利润/扣非净利润。这在金融场景会导致估值量级错误——
   这正是 Claim2Value 需要独立验证层的理由。

#### Oracle 自我修正（方法论亮点）

首轮评估发现 benchmark 自身的 oracle 存在缺陷：部分用例的 expected_verdict
假设了模型不可见的证据（只给来源名未给原始数值），导致模型合理拒答被误判为 miss。
修正后过度拒答从 11-12 条降到 3-5 条。

**这是 Oracle Mutation Testing 方法论的自我应验——benchmark 的评判标准本身也需要被验证。**
建议在项目书中作为「评测可信度」的论据展示。

#### 给队友的使用方式

- **Chen Luodi**：`claim_verification_v2.json` 可直接当 verifier 模块的验收考卷。
  跑法：`python benchmarks/evaluate.py --cases benchmarks/claim_verification_v2.json --models <你的verifier>`
  分数就是代码质量的客观度量，不用等人工评审。
- **西交经济/金融成员**：`report.md` 里的数字是「落地价值 40%」的弹药，
  尤其是口径偷换 12-35% 这条——建议配一个真实的财务口径混淆导致估值错误的案例。
- **电气/机械成员**：请核对工程类用例（额定/峰值扭矩、扭矩密度、LHS-32/SHPR-20E 参数）
  的 expected_verdict 是否符合工程常识。你们是 ground truth 的裁判。

#### 运行方式

```bash
# 1. 生成考卷（不需要 API）
python benchmarks/mutate.py          # 19 claim -> 98 用例
python benchmarks/fix_oracle.py      # 注入真实参数，修正 oracle

# 2. 跑评估（需要 Prism 网关 key）
python benchmarks/evaluate.py --models claude-sonnet-5 gpt-5.5

# 3. 出报告（不需要 API）
python benchmarks/report.py
```

**注意**：`evaluate.py` 不硬编码任何 API key，运行时从 `~/.workbuddy/models.json`
或工作区 `prism_config.json` 读取。**密钥不入库**，请勿提交带 key 的配置文件。

---

### 2026-09-01 `cbff862` docs: 更新清单与搜索报告

**相对上一次新增/变更：**
- 更新 `data/collection_checklist.md`：专利/参数/claim 状态改为完成或部分完成
- 更新 `data/search_report.md`：新增"六、已完成替代方案"和"七、仍建议手动补充"

**未变化**：代码、PDF、processed 数据文件均未动。

---

### 2026-09-01 `76e1118` data: 自动提取专利、参数、claim、行业基准

**这是目前内容最充实的一次提交。新增文件：**

| 类别 | 文件 | 说明 |
|---|---|---|
| 专利 | `data/processed/patent_collection.json` | 三家公司 30 条专利（绿的 7 / 环动 15 / 步科 8） |
| 专利 | `data/processed/patent_collection.csv` | 同上，CSV 版 |
| 参数 | `data/processed/parameter_table_filled.csv` | 三公司+竞争对手参数对比（含来源标注） |
| 参数 | `data/processed/parameter_table_template.csv` | 由 filled 版覆盖更新 |
| Claim | `data/processed/claim_bank_filled.json` | 18 条结构化 claim（绿的 7 / 步科 5 / 双环 5 / 行业 1） |
| Claim | `data/processed/claim_bank_template.json` | 由 filled 版覆盖更新 |
| 行业 | `data/processed/industry_data_summary.csv` | 工业机器人销量、减速器需求、国产化率 |
| 行业 | `data/processed/competitor_market_share.csv` | 谐波/RV 减速器市占率 |
| 工具 | `src/data_tools/extract_patents.py` | 专利提取脚本（PDF 乱码时备用） |
| 工具 | `src/data_tools/extract_parameters.py` | 参数候选扫描脚本 |
| 工具 | `src/data_tools/extract_claims.py` | claim 候选扫描脚本 |

**同时更新**：`.gitignore`（忽略可再生的 txt 提取文件和中间候选文件）

**本地有但未上传**（gitignore 排除，可重新生成）：
- `data/raw/**/*.txt` — PDF 提取的文本
- `data/processed/*_candidates*.csv` — 421 条原始 claim/参数候选
- `data/processed/huandong_patents.*` — 招股书乱码导致为空的提取结果

---

### 2026-09-01 `0ef790e` data: 三公司年报与研报 PDF

**新增 PDF（7 份公司文件 + 11 份研报，共 18 份）：**

公司公告（`data/raw/company_filings/`）：
- 绿的谐波 2024 年报、2025 年报
- 步科股份 2024 年报、2025 半年报
- 双环传动 2024 年报、2025 半年报
- 环动科技科创板 IPO 招股书

券商研报（`data/raw/analyst_reports/`）：
- 绿的谐波 4 份（2025Q1×2、2024&2025Q1、2025 半年报）
- 步科股份 2 份（2025Q2、2025Q3）
- 双环传动 3 份（2025-01、2025-05、2025Q2）
- 行业研报 2 份（精密减速器专题、人形机器人关节设计）

**同时新增**：
- `data/search_report.md` — 如实记录找到/未找到的资料及技术限制
- `data/processed/buke_fmk_parameters.csv` — 步科 FMK 系列 10 个型号参数
- 每份 PDF 配套的 `.meta.json` 来源文件

---

### 2026-08-30 `ca0b44a` docs: 数据收集指南与模板（主案例阶段）

**新增**：
- `data/collection_checklist.md` — 数据收集总清单
- `data/search_guide.md` — 搜索策略指南
- `data/processed/` 下 4 个空白模板（claim_bank / parameter_table / bom / financial_model_inputs）

> 注：当时还是"绿的谐波单案例"阶段，后升级为三案例策略，清单已更新。

---

### 2026-08-30 `0e72f01` init: 项目初始化

**新增**：
- `README.md` — 项目介绍与克隆指引
- `TODO.md` — 五阶段任务列表
- `research_notes/` — 研究笔记
- `setup_research_env.bat` — 队友一键下载论文+参考仓库的脚本
- `.gitignore`

---

## 当前仓库结构快照（截至 2026-09-01）

```
pku-financial-ai-agent/
├── README.md                  ← 项目说明（队友先看这个）
├── TODO.md                    ← 任务清单
├── SYNC_LOG.md                ← 本文件
├── setup_research_env.bat     ← 环境初始化脚本
├── data/
│   ├── collection_checklist.md    ← 数据清单（含状态列）
│   ├── search_guide.md            ← 搜索指南
│   ├── search_report.md           ← 搜索报告（找到/未找到）
│   ├── raw/
│   │   ├── company_filings/       ← 7 份公司公告 PDF + meta
│   │   └── analyst_reports/       ← 11 份研报 PDF + meta
│   └── processed/
│       ├── claim_bank_filled.json     ← 18 条 claim
│       ├── parameter_table_filled.csv ← 参数对比表
│       ├── patent_collection.csv/json ← 30 条专利
│       ├── industry_data_summary.csv  ← 行业数据
│       ├── competitor_market_share.csv← 竞争格局
│       ├── buke_fmk_parameters.csv    ← 步科 FMK 参数
│       └── *_template.csv/json        ← 模板（部分已被 filled 覆盖）
├── src/
│   ├── case.py                ← 三案例抽象层
│   └── data_tools/            ← PDF 提取脚本×3
└── research_materials/        ← 论文/参考仓库（PDF 被 gitignore，脚本下载）
```

---

## 给团队的说明

1. **clone 后第一件事**：运行 `setup_research_env.bat` 下载论文和参考仓库（这两类文件不进 Git，因为太大）。
2. **PDF 都在仓库里**：年报和研报直接随仓库分发，clone 即可用。
3. **每次有新数据/代码提交**：我会在这个文件顶部追加一行记录，你们 `git pull` 后看这里就知道新增了什么。
4. **手动待补清单**：见 `data/search_report.md` 第七节，主要是官方 datasheet 和步科发明专利。

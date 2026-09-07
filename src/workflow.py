"""
workflow.py — Claim2Value LangGraph 工作流编排层
=================================================

将 claim_verifier → state_verifier → evidence_ledger 串联成端到端验证流水线。

架构：
    Input(claim, source)
        │
        ▼
    ┌─────────────────────┐
    │ evidence_ledger_node │  证据收集 & 分级
    └────────┬────────────┘
             │
             ▼
    ┌─────────────────────┐
    │ state_verifier_node  │  规则层检查
    └────────┬────────────┘
             │
             ▼
    ┌─────────────────────┐
    │ claim_verifier_node  │  LLM 语义判断 + 合并
    └────────┬────────────┘
             │
             ▼
    ┌─────────────────────┐
    │ report_node          │  生成结构化报告
    └─────────────────────┘

注意：本项目不强依赖 langgraph 库（避免安装复杂性）。
如果 langgraph 可用则用它编排；否则用纯 Python 函数链。
两者输出完全一致。

用法：
    from src.workflow import run_verification

    result = run_verification(
        claim="绿的谐波2024年谐波减速器销量24.65万台，同比增长16.56%",
        source="国信证券研报：2024年谐波减速器及金属部件收入3.25亿元...",
    )
    print(result["verdict"])        # "supported"
    print(result["confidence"])     # 0.85
    print(result["rule_flags"])     # []
    print(result["report"])         # 格式化报告
"""

from __future__ import annotations
import json
from dataclasses import asdict
from typing import Dict, Any, List, Optional
from pathlib import Path

from src.state_verifier import StateVerifier
from src.evidence_ledger import EvidenceLedger, EvidenceLevel
from src.claim_verifier import ClaimVerifier, VerificationOutput
from src.engineering_analyzer import (
    DEFAULT_PARAMETER_CSV,
    Comparability,
    filter_comparable,
    load_and_normalize,
)
from src.economic_mapper import (
    DEFAULT_INDUSTRY_SUMMARY,
    DEFAULT_ONTOLOGY_PATH,
    DEFAULT_SHARE_CSV,
    IndustryData,
    generate_financial_model_inputs,
    load_aux_rows,
    load_ontology,
    map_engineering_to_economics,
)
from src.causal_critic import CausalCritic, CriticReview
from src.financial_model import (
    DEFAULT_INPUT_PATH,
    FORECAST_YEARS,
    FinancialModelInputs,
    detect_product_lines,
    run_all_scenarios,
)


# ============================================================
# 工作流节点
# ============================================================

def evidence_ledger_node(state: Dict) -> Dict:
    """节点 1：证据收集 & 分级"""
    source = state.get("source", "")
    ledger = EvidenceLedger()
    if source and source.strip():
        ledger.add_from_text(source)

    state["ledger"] = ledger
    state["trust_score"] = ledger.trust_score()
    state["has_evidence"] = not ledger.is_empty
    state["evidence_summary"] = ledger.summary()
    return state


def state_verifier_node(state: Dict) -> Dict:
    """节点 2：规则层检查"""
    claim = state.get("claim", "")
    source = state.get("source", "")
    verifier = StateVerifier()
    rule_result = verifier.verify(claim, source)

    state["rule_result"] = rule_result
    state["rule_verdict"] = rule_result.verdict_override
    state["rule_flags"] = rule_result.flags
    return state


def claim_verifier_node(state: Dict) -> Dict:
    """节点 3：LLM 语义判断 + 合并"""
    claim = state.get("claim", "")
    source = state.get("source", "")

    # 如果规则层已检出确定性问题且无证据场景已处理，
    # 仍然调用 LLM 以获取语义层面的 reasoning（但规则层 verdict 优先）
    model = state.get("model", "claude-sonnet-5")

    # 无证据 → 直接 abstain，不调 LLM
    if not state.get("has_evidence", False):
        state["verdict"] = "abstain"
        state["confidence"] = 0.1
        state["reasoning"] = "证据缺失，拒绝给出结论"
        state["verdict_source"] = "rule"
        state["llm_verdict"] = None
        state["llm_reasoning"] = None
        return state

    # 有证据 → 调用 LLM
    verifier = ClaimVerifier(model=model)
    result = verifier.verify(claim, source)

    state["verdict"] = result.verdict
    state["confidence"] = result.confidence
    state["reasoning"] = result.reasoning
    state["verdict_source"] = result.verdict_source
    state["llm_verdict"] = result.llm_verdict
    state["llm_confidence"] = result.llm_confidence
    state["llm_reasoning"] = result.llm_reasoning
    return state


def report_node(state: Dict) -> Dict:
    """节点 4：生成结构化报告"""
    verdict_cn = {
        "supported": "成立",
        "refuted": "不成立",
        "partially_supported": "部分成立",
        "definition_mismatch": "口径不符",
        "low_confidence": "来源不可靠",
        "abstain": "拒答",
        "error": "错误",
    }

    lines = []
    lines.append("=" * 60)
    lines.append("  Claim2Value 验证报告")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"  Claim: {state.get('claim', '')[:80]}...")
    lines.append(f"  判定: {verdict_cn.get(state.get('verdict', ''), state.get('verdict', ''))}")
    lines.append(f"  置信度: {state.get('confidence', 0):.2f}")
    lines.append(f"  判定来源: {state.get('verdict_source', '')}")
    lines.append(f"  证据可信度: {state.get('trust_score', 0):.2f}")
    lines.append("")

    # 规则层标记
    flags = state.get("rule_flags", [])
    if flags:
        lines.append("  规则层检出:")
        for f in flags:
            lines.append(f"    - {f}")
    else:
        lines.append("  规则层: 未检出异常")
    lines.append("")

    # LLM reasoning
    llm_r = state.get("llm_reasoning")
    if llm_r:
        lines.append(f"  LLM 推理: {llm_r[:200]}")
    lines.append("")
    lines.append("=" * 60)

    state["report"] = "\n".join(lines)
    return state


# ============================================================
# 工作流编排
# ============================================================

# 节点执行顺序
WORKFLOW_NODES = [
    ("evidence_ledger", evidence_ledger_node),
    ("state_verifier", state_verifier_node),
    ("claim_verifier", claim_verifier_node),
    ("report", report_node),
]


def run_verification(
    claim: str,
    source: str,
    model: str = "claude-sonnet-5",
) -> Dict[str, Any]:
    """
    运行端到端验证工作流。

    Args:
        claim: claim 文本
        source: 证据来源文本
        model: LLM 模型名

    Returns:
        包含所有节点输出的完整状态字典
    """
    state = {
        "claim": claim,
        "source": source,
        "model": model,
    }

    for name, node_fn in WORKFLOW_NODES:
        state = node_fn(state)
        state["_current_node"] = name

    return state


def run_batch(
    cases: List[Dict],
    model: str = "claude-sonnet-5",
    show_progress: bool = True,
) -> List[Dict]:
    """
    批量运行验证工作流。

    Args:
        cases: [{"case_id": ..., "mutated_claim": ..., "mutated_source": ...}, ...]
        model: LLM 模型名
        show_progress: 是否打印进度

    Returns:
        [{"case_id": ..., "verdict": ..., "judgement": ..., ...}, ...]
    """
    results = []
    total = len(cases)

    for i, case in enumerate(cases, 1):
        claim = case.get("mutated_claim", "")
        source = case.get("mutated_source", "")

        state = run_verification(claim, source, model)

        expected = case.get("expected_verdict", "")
        actual = state.get("verdict", "")
        hit = actual == expected

        row = {
            "case_id": case.get("case_id", ""),
            "mutation_type": case.get("mutation_type", ""),
            "expected_verdict": expected,
            "actual_verdict": actual,
            "judgement": "hit" if hit else "miss",
            "verdict_source": state.get("verdict_source", ""),
            "confidence": round(state.get("confidence", 0), 3),
            "rule_flags": state.get("rule_flags", []),
            "llm_verdict": state.get("llm_verdict"),
            "trust_score": round(state.get("trust_score", 0), 3),
        }
        results.append(row)

        if show_progress:
            mark = "HIT " if hit else "MISS"
            rule_tag = "[R]" if state.get("verdict_source") == "rule" else "[L]"
            print(f"[{i}/{total}] {mark} {rule_tag} {case.get('case_id',''):16s} "
                  f"exp={expected:20s} act={actual:20s}")

    return results


# ============================================================
# 财务影响链路（完整版工作流）
# ============================================================

# 验证结论门控：只有这两类 verdict 才允许进入财务链路。
# 显式常量而非内联集合，便于测试与审计。
GATE_VERDICTS = ("supported", "partially_supported")


def _rule_only_verification(claim: str, source: str) -> Dict[str, Any]:
    """
    纯本地规则层验证（无 LLM、无网络）。

    逻辑对齐 app.run_local_demo：规则层给出确定性 verdict_override 时采用之，
    否则保守 abstain。用于 run_financial_chain 在 LLM 配置缺失/调用失败时降级，
    保证本地可运行路径不中断。
    """
    ledger = EvidenceLedger()
    if source and source.strip():
        ledger.add_from_text(source)

    rule_result = StateVerifier().verify(claim, source)

    if rule_result.verdict_override:
        verdict = rule_result.verdict_override
        confidence = max(0.05, min(0.95, 0.5 + rule_result.confidence_adjustment))
        reasoning = "；".join(rule_result.flags)
        verdict_source = "rule_only_fallback"
    else:
        verdict = "abstain"
        confidence = 0.1
        reasoning = "规则层未发现确定性异常，但本地模式未调用 LLM，拒绝推断语义结论"
        verdict_source = "rule_only_fallback"

    state = {
        "claim": claim,
        "source": source,
        "ledger": ledger,
        "trust_score": ledger.trust_score(),
        "has_evidence": not ledger.is_empty,
        "evidence_summary": ledger.summary(),
        "rule_result": rule_result,
        "rule_verdict": rule_result.verdict_override,
        "rule_flags": rule_result.flags,
        "verdict": verdict,
        "confidence": confidence,
        "reasoning": reasoning,
        "verdict_source": verdict_source,
        "llm_verdict": None,
        "llm_confidence": None,
        "llm_reasoning": None,
    }
    return report_node(state)


def _financial_chain_verification(
    claim: str,
    source: str,
    model: str,
    local_only: bool,
    errors: List[Dict[str, str]],
) -> Dict[str, Any]:
    """
    财务链路的验证阶段。

    local_only=True 或 run_verification 因 LLM 配置缺失（RuntimeError）失败时，
    降级为纯规则层验证（_rule_only_verification），并在 errors 中留痕；
    其余异常同样降级并留痕，保证链路不断。
    """
    if not local_only:
        try:
            state = run_verification(claim, source, model)
            # claim_verifier 在 LLM 配置缺失时自身降级（verdict_source=rule_only_fallback）
            llm_skipped = state.get("verdict_source") == "rule_only_fallback"
            if llm_skipped:
                errors.append({
                    "stage": "verification",
                    "error": "LLM 验证配置缺失，claim_verifier 已降级为纯规则层验证",
                })
            state["verification_path"] = "rule_only" if llm_skipped else "full"
            return state
        except RuntimeError as exc:
            # LLM 网关配置缺失（load_prism_config 抛 RuntimeError）→ 本地降级
            errors.append({
                "stage": "verification",
                "error": f"LLM 验证不可用（{exc}），已降级为纯规则层验证",
            })
        except Exception as exc:  # 防御：任何验证异常都不拖垮财务链路
            errors.append({
                "stage": "verification",
                "error": f"run_verification 未预期失败（{type(exc).__name__}: {exc}），已降级为纯规则层验证",
            })

    state = _rule_only_verification(claim, source)
    state["verification_path"] = "rule_only"
    return state


def _aggregate_critic_annotation(causal: Dict[str, Any]) -> Dict[str, Any]:
    """
    从批判层审查结果聚合财务情景标注：

    - adjusted_confidence：取全部**定量**假设审查后 adjusted_confidence 的最小值
      （最保守口径；定量假设是财务模型的直接输入，定性假设不进入模型）；
      无定量假设时退回全部假设的最小值。
    - non_attributable_pct：取上述假设 non_attributable 区间上界的最大值
      （保守：只要有一条假设的某部分不可归因，就按最高比例提示）。

    两者均显式可解释，标注随情景输出，不得被吞掉。
    """
    reviews = causal.get("reviews", [])
    quantitative = [r for r in reviews if not r.get("qualitative_only")]
    pool = quantitative if quantitative else reviews
    if not pool:
        return {
            "adjusted_confidence": None,
            "non_attributable_pct": None,
            "basis": "批判层无审查记录，无法标注",
        }
    adj = min(r.get("adjusted_confidence", 0.0) for r in pool)
    na_upper = 0.0
    for r in pool:
        for na in r.get("non_attributable", []):
            rng = na.get("portion_pct_range") or [0.0, 0.0]
            if len(rng) >= 2:
                na_upper = max(na_upper, float(rng[1]))
    return {
        "adjusted_confidence": adj,
        "non_attributable_pct": na_upper,
        "basis": (
            f"取 {len(pool)} 条假设审查中 adjusted_confidence 最小值与"
            f"不可归因区间上界最大值（定量假设优先）"
        ),
    }


def run_financial_chain(
    claim: str,
    source: str,
    model: str = "claude-sonnet-5",
    target_company: Optional[str] = None,
    available_evidence: Optional[Dict[str, str]] = None,
    local_only: bool = False,
    parameter_csv: Path | str = DEFAULT_PARAMETER_CSV,
    ontology_path: Path | str = DEFAULT_ONTOLOGY_PATH,
    industry_summary_csv: Path | str = DEFAULT_INDUSTRY_SUMMARY,
    industry_share_csv: Path | str = DEFAULT_SHARE_CSV,
    model_inputs_csv: Path | str = DEFAULT_INPUT_PATH,
    critic: Optional[CausalCritic] = None,
) -> Dict[str, Any]:
    """
    运行完整财务影响链路：验证 → 门控 → 工程归一化 → 经济映射
    → 因果批判 → 财务三情景 → 综合报告。

    链路：
        claim + source
            │
            ▼
        验证流水线（复用 run_verification 节点；LLM 不可用时降级纯规则层）
            │  verdict ∈ GATE_VERDICTS 才放行，否则财务部分输出「不生成财务结论」
            ▼
        engineering_analyzer：参数归一化 + 可比性分级
            ▼
        economic_mapper：工程结论 → 经济假设（带 provenance 链）
            ▼
        causal_critic：替代解释 / 反事实需求 / adjusted_confidence / 不可归因
            ▼
        financial_model：三情景 EV / EBITDA / FCF（批判层标注随情景输出）
            ▼
        综合结构化报告（report_markdown）

    Args:
        claim: claim 文本
        source: 证据来源文本
        model: LLM 模型名（仅验证阶段使用；local_only=True 时忽略）
        target_company: 目标公司名；None 时用 ontology 的 target_company_default
        available_evidence: {evidence_key: 证据描述}，供批判层判定反事实需求是否满足
        local_only: True 时跳过 LLM，验证阶段直接走纯规则层（本地可复现路径）
        parameter_csv: 工程参数表路径（engineering_analyzer）
        ontology_path: tech_to_economics ontology JSON 路径
        industry_summary_csv / industry_share_csv: 行业数据 CSV 路径
        model_inputs_csv: 财务模型输入 CSV 路径（financial_model）
        critic: 自定义 CausalCritic（注入替代解释规则用）；None 用默认规则表

    Returns:
        结构化 dict：
            claim / source          —— 输入
            verification            —— 验证阶段输出（verdict/confidence/report 等）
            gate                    —— 门控结果（passed + reason）
            engineering             —— 归一化参数摘要（含可比性分级）；断链时为 None
            economics               —— 经济假设集（to_dict）；断链时为 None
            causal                  —— 批判层审查（to_dict，含 adjusted_confidence
                                      与 non_attributable）；断链时为 None
            financial               —— 三情景结果 + 批判层标注；
                                      status ∈ {"ok", "skipped", "failed"}
            errors                  —— [{"stage", "error"}]，记录断在哪一环
            report_markdown         —— 格式化综合报告

        每一步失败不崩溃整链：异常进 errors（带 stage 名），该阶段及下游
        输出置空/标记 skipped，验证报告与已完成的阶段照常输出。
    """
    errors: List[Dict[str, str]] = []

    # ── 阶段 1：验证流水线（复用现有节点；本地降级）──
    vstate = _financial_chain_verification(claim, source, model, local_only, errors)
    verification = {
        "verdict": vstate.get("verdict"),
        "confidence": vstate.get("confidence"),
        "verdict_source": vstate.get("verdict_source"),
        "rule_flags": vstate.get("rule_flags", []),
        "trust_score": vstate.get("trust_score"),
        "reasoning": vstate.get("reasoning"),
        "verification_path": vstate.get("verification_path"),
        "report": vstate.get("report", ""),
    }

    # ── 阶段 2：验证结论门控（显式、可测试）──
    verdict = verification["verdict"]
    gate_passed = verdict in GATE_VERDICTS
    if gate_passed:
        gate_reason = f"验证结论 {verdict} 属于放行集合 {list(GATE_VERDICTS)}，进入财务链路"
    else:
        gate_reason = (
            f"验证结论 {verdict} 不在放行集合 {list(GATE_VERDICTS)} 内，"
            f"不生成财务结论（仅输出验证报告）"
        )
    gate = {"passed": gate_passed, "allowed_verdicts": list(GATE_VERDICTS), "reason": gate_reason}

    engineering: Optional[Dict[str, Any]] = None
    economics: Optional[Dict[str, Any]] = None
    causal: Optional[Dict[str, Any]] = None
    financial: Dict[str, Any] = {"status": "skipped", "reason": gate_reason,
                                 "scenarios": {}, "critic_annotation": {}}

    if gate_passed:
        # ── 阶段 3：工程参数归一化 ──
        try:
            params = load_and_normalize(parameter_csv)
            comparable = filter_comparable(params)
            comparability_counts: Dict[str, int] = {}
            for p in params:
                comparability_counts[p.comparability.value] = (
                    comparability_counts.get(p.comparability.value, 0) + 1
                )
            engineering = {
                "n_rows": len(params),
                "n_comparable": len(comparable),
                "comparability_counts": comparability_counts,
                "rows": [p.to_dict() for p in params],
            }
        except Exception as exc:
            errors.append({"stage": "engineering",
                           "error": f"工程参数归一化失败（{type(exc).__name__}: {exc}），链路断于本环"})

        # ── 阶段 4：经济假设映射 ──
        ontology: Optional[Dict[str, Any]] = None
        assumption_set = None
        if engineering is not None:
            try:
                ontology = load_ontology(ontology_path)
                aux_rows = load_aux_rows(parameter_csv)
                industry_data = IndustryData.from_files(industry_summary_csv, industry_share_csv)
                # financial_base 是可选增强：模型输入缺失时降级为 None（归一乘数基准），
                # 让断点落在真正消费该文件的财务阶段
                try:
                    base_inputs = FinancialModelInputs.from_csv(model_inputs_csv)
                    financial_base = {
                        row.metric: row.value
                        for row in base_inputs.rows
                        if row.year == str(FORECAST_YEARS[0]) and row.input_type == "assumption"
                    }
                except Exception:
                    financial_base = None
                assumption_set = map_engineering_to_economics(
                    comparable,
                    ontology=ontology,
                    aux_rows=aux_rows,
                    target_company=target_company,
                    industry_data=industry_data,
                    financial_base=financial_base,
                )
                economics = {
                    "target_company": assumption_set.target_company,
                    "n_assumptions": len(assumption_set.assumptions),
                    "n_quantitative": len(assumption_set.quantitative()),
                    "assumption_set": assumption_set.to_dict(),
                }
            except Exception as exc:
                errors.append({"stage": "economics",
                               "error": f"经济假设映射失败（{type(exc).__name__}: {exc}），链路断于本环"})

        # ── 阶段 5：因果批判 ──
        critic_review: Optional[CriticReview] = None
        if assumption_set is not None:
            try:
                critic_review = (critic or CausalCritic()).review(
                    assumption_set, available_evidence=available_evidence)
                causal = critic_review.to_dict()
            except Exception as exc:
                errors.append({"stage": "causal",
                               "error": f"因果批判失败（{type(exc).__name__}: {exc}），链路断于本环"})

        # ── 阶段 6：财务三情景（批判层标注随输出）──
        if assumption_set is not None and critic_review is not None and ontology is not None:
            try:
                base_inputs = FinancialModelInputs.from_csv(model_inputs_csv)
                # 产品线按模型输入 CSV 自动识别（绿的 harmonic/joint；双环 rv/gear），
                # 保证经济映射的调整量落到该公司实际的产品线指标上
                product_lines = detect_product_lines(base_inputs.rows)
                adjusted_inputs = generate_financial_model_inputs(
                    assumption_set, base_inputs, ontology=ontology,
                    product_lines=product_lines)
                adjusted_inputs.validate(FORECAST_YEARS, product_lines)
                scenarios = run_all_scenarios(adjusted_inputs)
                financial = {
                    "status": "ok",
                    "reason": "财务三情景已基于批判层调整后的假设生成",
                    "model_inputs_path": str(model_inputs_csv),
                    "product_lines": product_lines,
                    "scenarios": {
                        name: {
                            "enterprise_value_bn": result["valuation"]["enterprise_value_bn"],
                            "ebitda_2027_bn": result["projections"][-1]["ebitda_bn"],
                            "fcf_2027_bn": result["projections"][-1]["fcf_bn"],
                            "revenue_2027_bn": result["projections"][-1]["revenue_bn"],
                            "model_status": result["model_status"],
                        }
                        for name, result in scenarios.items()
                    },
                    "critic_annotation": _aggregate_critic_annotation(causal or {}),
                }
            except Exception as exc:
                financial = {"status": "failed", "reason": f"财务模型运行失败：{exc}",
                             "scenarios": {}, "critic_annotation": {}}
                errors.append({"stage": "financial",
                               "error": f"财务模型运行失败（{type(exc).__name__}: {exc}），链路断于本环"})

    # ── 阶段 7：综合报告 ──
    report_markdown = _build_financial_report(
        claim=claim,
        verification=verification,
        gate=gate,
        engineering=engineering,
        economics=economics,
        causal=causal,
        financial=financial,
        errors=errors,
    )

    return {
        "claim": claim,
        "source": source,
        "verification": verification,
        "gate": gate,
        "engineering": engineering,
        "economics": economics,
        "causal": causal,
        "financial": financial,
        "errors": errors,
        "report_markdown": report_markdown,
    }


def _build_financial_report(
    claim: str,
    verification: Dict[str, Any],
    gate: Dict[str, Any],
    engineering: Optional[Dict[str, Any]],
    economics: Optional[Dict[str, Any]],
    causal: Optional[Dict[str, Any]],
    financial: Dict[str, Any],
    errors: List[Dict[str, str]],
) -> str:
    """组装财务链路的 Markdown 综合报告（验证 → 工程 → 经济 → 批判 → 财务）。"""
    verdict_cn = {
        "supported": "成立",
        "refuted": "不成立",
        "partially_supported": "部分成立",
        "definition_mismatch": "口径不符",
        "low_confidence": "来源不可靠",
        "abstain": "拒答",
        "error": "错误",
    }

    lines: List[str] = []
    lines.append("=" * 60)
    lines.append("  Claim2Value 财务影响链路报告")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"  Claim: {claim[:80]}")
    lines.append(f"  判定: {verdict_cn.get(verification.get('verdict', ''), verification.get('verdict', ''))}"
                 f"（{verification.get('verdict', '')}，置信度 {verification.get('confidence', 0):.2f}，"
                 f"来源 {verification.get('verdict_source', '')}）")
    if causal is not None:
        lines.append(f"  待补反事实证据: {causal.get('total_open_counterfactuals', 0)} 条"
                     f"（替代解释 {causal.get('total_alternatives', 0)} 条）")
    lines.append("")
    lines.append(f"  门控: {'放行' if gate.get('passed') else '拦截'} — {gate.get('reason', '')}")
    lines.append("")

    # 验证报告（复用验证流水线的格式化输出）
    lines.append("-" * 60)
    lines.append("【验证阶段】")
    lines.append(verification.get("report", ""))
    lines.append("")

    # 工程阶段
    lines.append("-" * 60)
    lines.append("【工程参数归一化】")
    if engineering is not None:
        lines.append(f"  共 {engineering['n_rows']} 行参数，可比较 {engineering['n_comparable']} 行"
                     f"（分级：{engineering['comparability_counts']}）")
    else:
        lines.append("  未执行（链路中断或门控拦截）")
    lines.append("")

    # 经济假设
    lines.append("-" * 60)
    lines.append("【经济假设映射】")
    if economics is not None:
        lines.append(f"  目标公司：{economics['target_company']}，"
                     f"假设 {economics['n_assumptions']} 条（定量 {economics['n_quantitative']} 条）")
        for a in economics["assumption_set"]["assumptions"]:
            kind = "定性" if a["qualitative_only"] else f"{a['delta_pct']:+.2%}"
            lines.append(f"    - [{a['rule_id']}] {a['variable_label']} → {kind}"
                         f"（证据 {a['evidence_grade']}，置信度 {a['confidence']}）")
    else:
        lines.append("  未执行（链路中断或门控拦截）")
    lines.append("")

    # 因果批判
    lines.append("-" * 60)
    lines.append("【因果批判层】")
    if causal is not None:
        for r in causal.get("reviews", []):
            kind = "定性" if r.get("qualitative_only") else "定量"
            lines.append(f"    - [{r.get('rule_id')}] {r.get('variable_label')}（{kind}）：置信度 "
                         f"{r.get('original_confidence')} → {r.get('adjusted_confidence')}"
                         f"，待补反事实 {r.get('n_open_counterfactuals')} 条")
            for na in r.get("non_attributable", []):
                lo, hi = na.get("portion_pct_range", [0, 0])
                lines.append(f"        不可归因 {lo:.0f}-{hi:.0f}%：{na.get('description', '')}")
    else:
        lines.append("  未执行（链路中断或门控拦截）")
    lines.append("")

    # 财务情景
    lines.append("-" * 60)
    lines.append("【财务三情景】")
    if financial.get("status") == "ok":
        ann = financial.get("critic_annotation", {})
        adj = ann.get("adjusted_confidence")
        na_pct = ann.get("non_attributable_pct")
        for name, s in financial.get("scenarios", {}).items():
            lines.append(f"    {name:8s} EV={s['enterprise_value_bn']:.4f} bn"
                         f"  2027 EBITDA={s['ebitda_2027_bn']:.4f} bn"
                         f"  2027 FCF={s['fcf_2027_bn']:.4f} bn")
            if adj is not None and na_pct is not None:
                lines.append(f"        ⚠ 该情景基于置信度 {adj:.2f} 的假设，"
                             f"其中最高 {na_pct:.0f}% 不可归因（{ann.get('basis', '')}）")
    else:
        lines.append(f"  {financial.get('reason', '')}")
    lines.append("")

    # 错误与断链
    if errors:
        lines.append("-" * 60)
        lines.append("【错误与断链】")
        for e in errors:
            lines.append(f"    [{e['stage']}] {e['error']}")
        lines.append("")

    lines.append("=" * 60)
    return "\n".join(lines)


# ============================================================
# CLI 入口
# ============================================================
if __name__ == "__main__":
    import sys
    import argparse
    import io

    REPO_ROOT = Path(__file__).resolve().parent.parent

    ap = argparse.ArgumentParser(description="Claim2Value 验证工作流")
    ap.add_argument("--model", default="claude-sonnet-5")
    ap.add_argument("--cases", default=str(REPO_ROOT / "benchmarks" / "claim_verification_v2.json"))
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out", default="")
    ap.add_argument("--single", action="store_true", help="单条验证模式")
    ap.add_argument("--full", action="store_true", help="完整财务影响链路模式（验证+工程+经济+批判+财务）")
    ap.add_argument("--claim", default="", help="单条验证的 claim 文本")
    ap.add_argument("--source", default="", help="单条验证的 source 文本")
    ap.add_argument("--local-only", action="store_true", help="--full 模式下跳过 LLM，纯本地规则路径")
    args = ap.parse_args()

    if args.full:
        # 完整财务影响链路
        if not args.claim:
            print("请用 --claim 提供 claim 文本")
            sys.exit(1)

        result = run_financial_chain(
            args.claim, args.source, args.model, local_only=args.local_only,
        )
        print(result.get("report_markdown", ""))
        print()
        print("详细输出:")
        print(json.dumps({
            "verdict": result["verification"]["verdict"],
            "gate_passed": result["gate"]["passed"],
            "engineering_rows": (result["engineering"] or {}).get("n_rows"),
            "n_assumptions": (result["economics"] or {}).get("n_assumptions"),
            "open_counterfactuals": (result["causal"] or {}).get("total_open_counterfactuals"),
            "financial_status": result["financial"]["status"],
            "scenarios": {
                name: s["enterprise_value_bn"]
                for name, s in result["financial"].get("scenarios", {}).items()
            },
            "errors": result["errors"],
        }, ensure_ascii=False, indent=2))

    elif args.single:
        # 单条验证
        if not args.claim:
            print("请用 --claim 提供 claim 文本")
            sys.exit(1)

        state = run_verification(args.claim, args.source, args.model)
        print(state.get("report", ""))
        print()
        print("详细输出:")
        print(json.dumps({
            "verdict": state.get("verdict"),
            "confidence": round(state.get("confidence", 0), 3),
            "verdict_source": state.get("verdict_source"),
            "rule_flags": state.get("rule_flags", []),
            "llm_verdict": state.get("llm_verdict"),
            "trust_score": round(state.get("trust_score", 0), 3),
        }, ensure_ascii=False, indent=2))

    else:
        # 批量验证
        cases_path = Path(args.cases)
        if not cases_path.exists():
            print(f"用例文件不存在: {cases_path}")
            sys.exit(1)

        data = json.loads(io.open(cases_path, encoding="utf-8").read())
        cases = data["cases"]
        if args.limit:
            cases = cases[:args.limit]

        print(f"用例: {len(cases)}  模型: {args.model}")
        print("=" * 70)

        results = run_batch(cases, args.model)

        # 统计
        hit = sum(1 for r in results if r["judgement"] == "hit")
        miss = sum(1 for r in results if r["judgement"] == "miss")
        total = hit + miss

        print(f"\n{'=' * 70}")
        print(f"总准确率: {hit}/{total} = {hit/total*100:.1f}%")

        # 按扰动类型
        from collections import defaultdict
        by_type = defaultdict(lambda: {"hit": 0, "miss": 0})
        for r in results:
            by_type[r["mutation_type"]][r["judgement"]] += 1

        print(f"\n按扰动类型:")
        for mtype, stats in sorted(by_type.items()):
            acc = stats["hit"] / (stats["hit"] + stats["miss"]) if (stats["hit"] + stats["miss"]) else 0
            print(f"  {mtype:25s} {acc*100:5.1f}%  ({stats['hit']}/{stats['hit']+stats['miss']})")

        if args.out:
            out_path = Path(args.out)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with io.open(out_path, "w", encoding="utf-8") as f:
                for r in results:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
            print(f"\n结果已写入: {out_path}")

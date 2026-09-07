"""
test_e2e_regression.py — 端到端回归用例
======================================

覆盖 TODO 验收标准 3/4：财务模型可复算、证据链、Demo 输出、workflow 本地路径。
每条用例失败可定位到具体 fixture；不依赖未合并 PR 的模块
（engineering_analyzer / economic_mapper / causal_critic 不在 main 上，勿 import）。

注意：若 PR #8（workflow 财务链路 + claim_verifier 降级修复）已合并进 main，
TestWorkflowLocal::test_llm_unavailable_raises 需改为断言降级输出，
因为 PR #8 把「无 LLM 配置」从抛 RuntimeError 改为保守降级。
"""

import json
import math
import unittest
from pathlib import Path

from app import run_local_demo
from src.evidence_ledger import Evidence, EvidenceLedger
from src.financial_model import FinancialModelInputs, run_all_scenarios
from src.workflow import run_verification

REPO_ROOT = Path(__file__).resolve().parent.parent
INPUTS_CSV = REPO_ROOT / "data" / "processed" / "green_harmonic_model_inputs.csv"
RESULTS_JSON = REPO_ROOT / "data" / "processed" / "green_harmonic_model_results.json"
DEMO_FIXTURE = REPO_ROOT / "data" / "processed" / "local_demo_fixture.json"


def assert_nested_close(test, recomputed, stored, path="root"):
    """递归比较：数值容差 1e-6，其余类型严格相等。"""
    if isinstance(stored, float) or isinstance(recomputed, float):
        test.assertTrue(
            math.isclose(float(recomputed), float(stored), rel_tol=0, abs_tol=1e-6),
            f"{path}: {recomputed} != {stored}")
    elif isinstance(stored, dict):
        test.assertEqual(set(recomputed), set(stored), f"{path}: key 集合不一致")
        for k in stored:
            assert_nested_close(test, recomputed[k], stored[k], f"{path}.{k}")
    elif isinstance(stored, list):
        test.assertEqual(len(recomputed), len(stored), f"{path}: 长度不一致")
        for i, item in enumerate(stored):
            assert_nested_close(test, recomputed[i], item, f"{path}[{i}]")
    else:
        test.assertEqual(recomputed, stored, f"{path}")


class TestFinancialReproducibility(unittest.TestCase):
    """验收标准 2：固定 fixture 三情景可复算，且披露/假设/计算分栏隔离。"""

    def test_three_scenarios_match_stored_results(self):
        inputs = FinancialModelInputs.from_csv(INPUTS_CSV)
        recomputed = run_all_scenarios(inputs)
        stored = json.loads(RESULTS_JSON.read_text(encoding="utf-8"))
        self.assertEqual(set(recomputed), {"base", "upside", "downside"})
        for scenario in stored:
            assert_nested_close(self, recomputed[scenario], stored[scenario],
                                path=scenario)

    def test_input_type_isolation(self):
        """输入表不得包含 calculated 行（calculated 结果不得写回输入表）。"""
        import csv
        with open(INPUTS_CSV, encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        input_types = {r["input_type"] for r in rows}
        self.assertIn("historical", input_types)
        self.assertIn("assumption", input_types)
        self.assertNotIn("calculated", input_types)


class TestEvidenceChain(unittest.TestCase):
    """证据链：trust_score 有界、空账本拒答、重复证据不重复加分。"""

    def _ledger_from_fixture(self):
        fixture = json.loads(DEMO_FIXTURE.read_text(encoding="utf-8"))
        ev = fixture["evidence"]
        ledger = EvidenceLedger()
        ledger.add(Evidence(
            source_text=ev["source_text"],
            source_url=ev.get("source_url"),
        ))
        return ledger

    def test_trust_score_bounded(self):
        score = self._ledger_from_fixture().trust_score()
        self.assertGreater(score, 0.0)
        self.assertLessEqual(score, 1.0)

    def test_empty_ledger_scores_zero(self):
        self.assertEqual(EvidenceLedger().trust_score(), 0.0)

    def test_duplicate_evidence_not_double_counted(self):
        """同一证据重复 add：指纹相同，trust_score 不得因副本上升。"""
        fixture = json.loads(DEMO_FIXTURE.read_text(encoding="utf-8"))
        text = fixture["evidence"]["source_text"]

        single = EvidenceLedger()
        single.add(Evidence(source_text=text))

        dup = EvidenceLedger()
        for _ in range(3):
            dup.add(Evidence(source_text=text))

        self.assertEqual(dup.trust_score(), single.trust_score())


class TestDemoOutput(unittest.TestCase):
    """验收标准 3：Demo 输出五要素齐全，空证据时指出证据不足。"""

    def test_five_elements_present(self):
        result = run_local_demo()
        # ① Claim ② 证据 ③ StateVerifier 结论 ④ 财务情景 ⑤ 限制说明
        self.assertTrue(result.get("claim"))                         # ①
        self.assertTrue(result["demo_case"]["evidence"])             # ②
        self.assertIn("verdict", result["verification"])             # ③
        for scenario in ("base", "upside", "downside"):              # ④ 财务情景
            self.assertIn(scenario, result["financial"]["scenarios"])
        self.assertIn("limitations", result["demo_case"])            # ⑤

    def test_empty_evidence_abstains(self, ):
        fixture = json.loads(DEMO_FIXTURE.read_text(encoding="utf-8"))
        fixture["evidence"]["source_text"] = ""
        import tempfile, os
        fd, tmp = tempfile.mkstemp(suffix=".json")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(fixture, f, ensure_ascii=False)
            result = run_local_demo(fixture_path=tmp)
            self.assertEqual(result["verification"]["verdict"], "abstain")
            self.assertEqual(result["verification"]["trust_score"], 0.0)
            # 无证据 → 门控拦截，不生成财务结论
            self.assertFalse(result["gate"]["passed"])
            self.assertEqual(result["financial"]["status"], "skipped")
        finally:
            os.unlink(tmp)


class TestWorkflowLocal(unittest.TestCase):
    """workflow 本地可运行路径（无外部 API）。"""

    def _has_llm_config(self):
        return (REPO_ROOT.parent / "prism_config.json").exists() or \
               (Path.home() / ".workbuddy" / "models.json").exists()

    def test_empty_evidence_abstain_path(self):
        """无证据 → 不触碰 LLM，直接拒答并出报告（验收标准 1 的无 API 路径）。"""
        if self._has_llm_config():
            self.skipTest("本机存在 LLM 配置；空证据路径不依赖配置，但为保持环境一致跳过")
        state = run_verification("某公司收入下降30%", "")
        self.assertEqual(state["verdict"], "abstain")
        self.assertIn("confidence", state)
        self.assertIn("报告", state["report"] or state.get("report", ""))

    def test_llm_unavailable_degrades_to_rule_only(self):
        """main 契约（PR #8 起）：有证据但无 LLM 配置 → 保守降级，不抛异常。

        claim_verifier 在 LLM 配置缺失时内部降级为纯规则层验证，
        输出 verdict_source == 'rule_only_fallback'，本地路径不中断。
        """
        if self._has_llm_config():
            self.skipTest("本机存在 LLM 配置，无法测试无配置路径")
        state = run_verification("某公司收入下降30%", "研报指出收入同比下降30%以上")
        self.assertEqual(state.get("verdict_source"), "rule_only_fallback")
        self.assertIn(state.get("verdict"), ("support", "partially_supported", "dispute", "abstain"))


if __name__ == "__main__":
    unittest.main()

# -*- coding: utf-8 -*-
"""双环传动估值链全链路移植回归（Phase 3C）。

证明 run_financial_chain 对第二家公司（rv/gear 两条产品线）端到端可跑：
验证 → 门控 → 工程归一化 → 经济映射（带 product_line_scope 的 ontology 变体）
→ 因果批判 → 财务三情景。claim 与证据文本取自 Claim Bank 已验证条目
SH_004（环动科技招股书客户名单，页码级出处）。
"""
import json
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
import sys
sys.path.insert(0, str(REPO_ROOT))

from src.workflow import run_financial_chain  # noqa: E402

CLAIM_BANK = REPO_ROOT / "data" / "processed" / "claim_bank_filled.json"
INPUTS_CSV = REPO_ROOT / "data" / "processed" / "shuanghuan_model_inputs.csv"
ONTOLOGY = REPO_ROOT / "data" / "processed" / "tech_to_economics_ontology_shuanghuan.json"


def _shuanghuan_claim_source() -> tuple[str, str]:
    bank = json.loads(CLAIM_BANK.read_text(encoding="utf-8"))
    claims = bank if isinstance(bank, list) else bank.get("claims", bank)
    sh = next(c for c in claims if c.get("claim_id") == "SH_004")
    ev = sh["evidence_list"][0]
    # 有意省略"国内"限定词：source 含"国内知名品牌制造商"，
    # 规则层按限定词缺失给 partially_supported（与本地演示门控同机制）
    claim = ("环动科技下游客户已覆盖埃斯顿、埃夫特、卡诺普、"
             "爱仕达旗下钱江机器人等知名机器人制造商")
    return claim, ev["source"] + "\n" + ev["excerpt"]


class TestShuanghuanChain(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        claim, source = _shuanghuan_claim_source()
        cls.result = run_financial_chain(
            claim=claim,
            source=source,
            target_company="双环传动/环动科技",
            local_only=True,
            model_inputs_csv=INPUTS_CSV,
            ontology_path=ONTOLOGY,
        )

    def test_verification_and_gate(self):
        self.assertEqual(self.result["verification"]["verdict"], "partially_supported")
        self.assertTrue(self.result["gate"]["passed"])

    def test_engineering_and_economics_run(self):
        self.assertEqual(self.result["errors"], [])
        self.assertIsNotNone(self.result["engineering"])
        self.assertIsNotNone(self.result["economics"])
        self.assertGreater(self.result["economics"]["n_assumptions"], 0)

    def test_financial_three_scenarios_positive(self):
        fin = self.result["financial"]
        self.assertEqual(fin["status"], "ok")
        self.assertEqual(sorted(fin["scenarios"]), ["base", "downside", "upside"])
        self.assertEqual(fin["product_lines"], ["gear", "rv"])
        for name, scenario in fin["scenarios"].items():
            self.assertGreater(scenario["enterprise_value_bn"], 0.0, name)
            self.assertGreater(scenario["revenue_2027_bn"], 0.0, name)

    def test_critic_annotation_present(self):
        """批判层标注必须随情景输出（adjusted_confidence / non_attributable）。"""
        ann = self.result["financial"]["critic_annotation"]
        self.assertIsNotNone(ann["adjusted_confidence"])
        self.assertLessEqual(ann["adjusted_confidence"], 1.0)


if __name__ == "__main__":
    unittest.main()

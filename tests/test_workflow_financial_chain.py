"""workflow 财务影响链路测试。

覆盖：
- 验证结论门控：refuted / abstain 不进入财务链路，但仍输出验证报告
- 端到端本地链路：真实 fixture 跑通（验证 → 工程 → 经济 → 批判 → 财务三情景）
- 综合报告结构完整（verification / engineering / economics / causal /
  financial / report_markdown / errors）
- 断链容错：某阶段失败进 errors 并说明断点，不崩溃整链
- LLM 不可用时验证阶段自动降级纯规则层（本地可复现路径）
- 现有 `python -m src.workflow --single` CLI 行为不变
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.workflow import GATE_VERDICTS, run_financial_chain  # noqa: E402

FIXTURE_PATH = REPO_ROOT / "data" / "processed" / "local_demo_fixture.json"
MISSING_CSV = REPO_ROOT / "data" / "processed" / "__definitely_missing__.csv"


def load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def run_fixture_chain(**kwargs) -> dict:
    fx = load_fixture()
    kwargs.setdefault("local_only", True)
    return run_financial_chain(fx["claim"], fx["evidence"]["source_text"], **kwargs)


class GateTests(unittest.TestCase):
    """验证结论门控：只有 supported/partially_supported 进入财务链路。"""

    def test_refuted_claim_is_blocked_from_financial_chain(self):
        # 时间错位 → 规则层 refuted
        result = run_financial_chain(
            claim="绿的谐波2025年谐波减速器销量24.65万台",
            source="国信证券研报：2024年谐波减速器销量24.65万台。",
            local_only=True,
        )
        self.assertEqual(result["verification"]["verdict"], "refuted")
        self.assertFalse(result["gate"]["passed"])
        self.assertEqual(result["financial"]["status"], "skipped")
        self.assertIn("不生成财务结论", result["financial"]["reason"])
        # 门控拦截不算错误
        self.assertEqual(result["errors"], [])
        # 财务各阶段未执行
        self.assertIsNone(result["engineering"])
        self.assertIsNone(result["economics"])
        self.assertIsNone(result["causal"])
        # 验证报告照常输出
        self.assertIn("Claim2Value 验证报告", result["verification"]["report"])
        self.assertIn("不生成财务结论", result["report_markdown"])

    def test_abstain_claim_is_blocked_from_financial_chain(self):
        # 空 source → abstain
        result = run_financial_chain(
            claim="绿的谐波减重30%以上",
            source="",
            local_only=True,
        )
        self.assertEqual(result["verification"]["verdict"], "abstain")
        self.assertFalse(result["gate"]["passed"])
        self.assertEqual(result["financial"]["status"], "skipped")

    def test_gate_verdicts_explicit(self):
        self.assertEqual(tuple(GATE_VERDICTS), ("supported", "partially_supported"))


class EndToEndLocalChainTests(unittest.TestCase):
    """真实 fixture 的端到端本地链路（无 LLM、无网络）。"""

    def test_full_chain_on_real_fixture(self):
        result = run_fixture_chain()

        # 验证：fixture 经规则层（限定词缺失）→ partially_supported，门控放行
        self.assertEqual(result["verification"]["verdict"], "partially_supported")
        self.assertTrue(result["gate"]["passed"])

        # 工程：真实参数表已归一化
        self.assertIsNotNone(result["engineering"])
        self.assertGreater(result["engineering"]["n_rows"], 0)
        self.assertGreater(result["engineering"]["n_comparable"], 0)

        # 经济：假设集非空，含定量与定性假设
        self.assertIsNotNone(result["economics"])
        self.assertGreater(result["economics"]["n_assumptions"], 0)
        self.assertGreater(result["economics"]["n_quantitative"], 0)

        # 批判层：adjusted_confidence 与不可归因必须出现在输出中（不许吞掉）
        self.assertIsNotNone(result["causal"])
        self.assertGreater(result["causal"]["total_open_counterfactuals"], 0)
        for review in result["causal"]["reviews"]:
            self.assertLessEqual(
                review["adjusted_confidence"], review["original_confidence"])

        # 财务：三情景齐全且 EV 为正
        self.assertEqual(result["financial"]["status"], "ok")
        scenarios = result["financial"]["scenarios"]
        self.assertEqual(set(scenarios), {"base", "upside", "downside"})
        for name, s in scenarios.items():
            self.assertGreater(s["enterprise_value_bn"], 0, name)
            self.assertIn("ebitda_2027_bn", s)
            self.assertIn("fcf_2027_bn", s)

        # 批判层标注随情景输出
        ann = result["financial"]["critic_annotation"]
        self.assertIsNotNone(ann["adjusted_confidence"])
        self.assertGreater(ann["non_attributable_pct"], 0)

        # 报告头部包含待补反事实证据数量
        self.assertIn("待补反事实证据", result["report_markdown"])
        self.assertIn(
            str(result["causal"]["total_open_counterfactuals"]),
            result["report_markdown"],
        )
        # 报告标注「该情景基于置信度 x 的假设，其中 y% 不可归因」
        self.assertIn("该情景基于置信度", result["report_markdown"])
        self.assertIn("不可归因", result["report_markdown"])

    def test_llm_unavailable_falls_back_to_rule_only(self):
        # 不显式 local_only：无 LLM 配置时验证阶段自动降级，链路仍跑通
        if (REPO_ROOT.parent / "prism_config.json").exists() or \
           (Path.home() / ".workbuddy" / "models.json").exists():
            self.skipTest("本机存在 LLM 配置，无法测试降级路径")
        result = run_fixture_chain(local_only=False)
        self.assertEqual(result["verification"]["verification_path"], "rule_only")
        stages = [e["stage"] for e in result["errors"]]
        self.assertIn("verification", stages)
        # 降级不阻断财务链路
        self.assertEqual(result["financial"]["status"], "ok")


class ReportStructureTests(unittest.TestCase):
    """综合报告结构完整。"""

    def test_top_level_keys(self):
        result = run_fixture_chain()
        for key in ("verification", "gate", "engineering", "economics",
                    "causal", "financial", "errors", "report_markdown"):
            self.assertIn(key, result)

    def test_report_markdown_sections(self):
        result = run_fixture_chain()
        md = result["report_markdown"]
        for section in ("【验证阶段】", "【工程参数归一化】", "【经济假设映射】",
                        "【因果批判层】", "【财务三情景】"):
            self.assertIn(section, md)


class BrokenChainToleranceTests(unittest.TestCase):
    """断链容错：单阶段失败进 errors，不崩溃整链。"""

    def test_missing_parameter_csv_breaks_at_engineering(self):
        result = run_fixture_chain(parameter_csv=MISSING_CSV)
        self.assertTrue(result["gate"]["passed"])  # 门控仍放行
        stages = [e["stage"] for e in result["errors"]]
        self.assertIn("engineering", stages)
        self.assertIsNone(result["engineering"])
        self.assertIsNone(result["economics"])
        self.assertIsNone(result["causal"])
        self.assertEqual(result["financial"]["status"], "skipped")
        # 验证报告照常输出
        self.assertIn("Claim2Value 验证报告", result["verification"]["report"])
        # 报告说明断链
        self.assertIn("【错误与断链】", result["report_markdown"])

    def test_missing_model_inputs_fails_at_financial(self):
        result = run_fixture_chain(model_inputs_csv=MISSING_CSV)
        stages = [e["stage"] for e in result["errors"]]
        self.assertIn("financial", stages)
        # 上游阶段正常完成
        self.assertIsNotNone(result["engineering"])
        self.assertIsNotNone(result["economics"])
        self.assertIsNotNone(result["causal"])
        # 财务阶段标记 failed 而非崩溃
        self.assertEqual(result["financial"]["status"], "failed")
        self.assertEqual(result["financial"]["scenarios"], {})


class SingleCliRegressionTests(unittest.TestCase):
    """现有 `python -m src.workflow --single` CLI 行为不变。"""

    def _run_cli(self, extra_args):
        env = dict(os.environ)
        env["PYTHONIOENCODING"] = "utf-8"
        proc = subprocess.run(
            [sys.executable, "-m", "src.workflow", *extra_args],
            cwd=REPO_ROOT, env=env,
            capture_output=True, timeout=120,
        )
        # Windows 下父进程默认按 GBK 解码管道，改为显式 UTF-8
        proc.stdout_text = proc.stdout.decode("utf-8", errors="replace")
        return proc

    def test_single_mode_without_source_still_abstains(self):
        proc = self._run_cli(["--single", "--claim", "测试claim"])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("Claim2Value 验证报告", proc.stdout_text)
        self.assertIn("拒答", proc.stdout_text)

    def test_single_mode_requires_claim(self):
        proc = self._run_cli(["--single"])
        self.assertEqual(proc.returncode, 1)

    def test_full_mode_runs_chain(self):
        fx = load_fixture()
        proc = self._run_cli([
            "--full", "--local-only",
            "--claim", fx["claim"], "--source", fx["evidence"]["source_text"],
        ])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("财务影响链路报告", proc.stdout_text)
        self.assertIn('"financial_status": "ok"', proc.stdout_text)


if __name__ == "__main__":
    unittest.main()

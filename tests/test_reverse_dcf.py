# -*- coding: utf-8 -*-
"""反向 DCF（reverse_dcf）回归测试。

口径：target = base EV → 隐含倍数 ≈ 1；target 明显高于 base → 倍数 > 1；
不可解区间显式报错。所有断言基于默认 fixture 输入，确定性可复算。
"""
import unittest

from src.financial_model import (
    DEFAULT_INPUT_PATH,
    FinancialModelInputs,
    reverse_dcf,
    run_model,
)


class TestReverseDcf(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs = FinancialModelInputs.from_csv(DEFAULT_INPUT_PATH)

    def test_target_equals_base_ev_gives_multiplier_one(self):
        base_ev = run_model(self.inputs, "base")["valuation"]["enterprise_value_bn"]
        result = reverse_dcf(self.inputs, base_ev)
        self.assertAlmostEqual(
            result["implied_volume_multiplier"], 1.0, delta=1e-3)
        self.assertAlmostEqual(
            result["ev_at_implied_multiplier_bn"], base_ev, delta=1e-6)

    def test_higher_target_gives_higher_multiplier(self):
        base_ev = run_model(self.inputs, "base")["valuation"]["enterprise_value_bn"]
        low = reverse_dcf(self.inputs, base_ev * 1.2)
        high = reverse_dcf(self.inputs, base_ev * 1.5)
        self.assertGreater(
            high["implied_volume_multiplier"], low["implied_volume_multiplier"])
        self.assertGreater(low["implied_volume_multiplier"], 1.0)

    def test_out_of_range_target_raises(self):
        base_ev = run_model(self.inputs, "base")["valuation"]["enterprise_value_bn"]
        with self.assertRaises(ValueError):
            reverse_dcf(self.inputs, base_ev * 1000)

    def test_result_contains_scenario_comparison(self):
        base_ev = run_model(self.inputs, "base")["valuation"]["enterprise_value_bn"]
        result = reverse_dcf(self.inputs, base_ev * 2)
        self.assertIn("base", result["scenario_evs_bn"])
        self.assertIn("upside", result["scenario_evs_bn"])
        self.assertIn("downside", result["scenario_evs_bn"])
        # 目标设为 2 倍 base EV 时，base 情景距目标约 -50%
        self.assertAlmostEqual(
            result["gap_vs_target_pct"]["base"], -50.0, delta=0.5)


if __name__ == "__main__":
    unittest.main()

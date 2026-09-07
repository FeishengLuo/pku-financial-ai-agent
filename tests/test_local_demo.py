import unittest

from app import run_local_demo


class LocalDemoTests(unittest.TestCase):
    def test_demo_is_local_and_conservative(self):
        """Demo 走串联全链路（local_only），验证->门控->财务传导真实存在。"""
        result = run_local_demo()

        # 本地无 API
        self.assertNotIn("llm", str(result.get("verification", {}).get("verdict_source", "")))

        # 规则层抓住限定词缺失 -> partially_supported
        verification = result["verification"]
        self.assertEqual(verification["verdict"], "partially_supported")
        self.assertIn("限定词缺失", str(verification.get("rule_flags", [])))

        # 门控放行
        self.assertTrue(result["gate"]["passed"])

        # 财务三情景带 EV（批判层调整后假设）
        financial = result["financial"]
        self.assertEqual(financial["status"], "ok")
        self.assertIn("base", financial["scenarios"])
        self.assertIn("enterprise_value_bn", financial["scenarios"]["base"])

    def test_demo_engineering_drives_economics(self):
        """工程参数确凿传导进经济假设（可量化假设带 delta_pct）。"""
        result = run_local_demo()
        assumptions = result["economics"]["assumption_set"]["assumptions"]
        quantitative = [a for a in assumptions if not a.get("qualitative_only")]
        self.assertTrue(
            quantitative,
            "期望至少有可量化经济假设从工程参数传导而来",
        )
        self.assertTrue(
            any(a.get("delta_pct") is not None for a in quantitative),
            "可量化假设应带 delta_pct（工程参数真实调整的痕迹）",
        )


if __name__ == "__main__":
    unittest.main()
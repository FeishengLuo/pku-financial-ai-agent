# -*- coding: utf-8 -*-
"""延迟基准脚本的冒烟回归：只验证可运行与产物结构，不断言具体毫秒值
（延迟随机器波动，具体数字以 benchmarks/latency_report.md 为准）。"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from scripts.benchmark_latency import run_once, FIXTURE, OUT  # noqa: E402


class TestLatencyBenchmark(unittest.TestCase):
    def test_run_once_returns_positive_ms(self):
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        ms = run_once(fixture)
        self.assertIsInstance(ms, float)
        self.assertGreater(ms, 0.0)
        # 宽边界：本地规则链路单次要能在 60 秒内完成（防死循环级劣化）
        self.assertLess(ms, 60_000.0)

    def test_script_writes_report_with_stats(self):
        r = subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "benchmark_latency.py"),
             "--n", "3"],
            capture_output=True, timeout=300)
        self.assertEqual(r.returncode, 0, r.stderr.decode("utf-8", "replace"))
        report = OUT.read_text(encoding="utf-8")
        self.assertIn("p50", report)
        self.assertIn("N | 3", report)
        self.assertIn("无 LLM、无网络", report)


if __name__ == "__main__":
    unittest.main()

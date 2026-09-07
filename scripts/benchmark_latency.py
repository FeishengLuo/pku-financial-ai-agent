# -*- coding: utf-8 -*-
"""C7 效率基准：本地全链路延迟测量（无 LLM / 无网络）。

跑 N 次 ``run_financial_chain(local_only=True)``（与 app.py Demo 同一条链路：
Claim → 验证 → 工程归一化 → 经济映射 → 因果批判 → 财务三情景），
记录 p50 / p95 / min / max，连同环境信息写入 ``benchmarks/latency_report.md``。

用法：
    python scripts/benchmark_latency.py            # 默认 N=30
    python scripts/benchmark_latency.py --n 50

注意：首次运行含 import 与数据加载预热，统一按"第 1 次单独记录、
统计口径为第 2 次起"处理，避免冷启动污染分布。
"""
from __future__ import annotations

import argparse
import json
import platform
import statistics
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.workflow import run_financial_chain  # noqa: E402

FIXTURE = REPO_ROOT / "data" / "processed" / "local_demo_fixture.json"
OUT = REPO_ROOT / "benchmarks" / "latency_report.md"


def run_once(fixture: dict) -> float:
    t0 = time.perf_counter()
    run_financial_chain(
        claim=fixture["claim"],
        source=fixture["evidence"]["source_text"],
        local_only=True,
    )
    return (time.perf_counter() - t0) * 1000.0


def main() -> None:
    ap = argparse.ArgumentParser(description="本地全链路延迟基准（无 LLM/无网络）")
    ap.add_argument("--n", type=int, default=30, help="运行次数（默认 30）")
    ap.add_argument("--out", default=str(OUT),
                    help="报告输出路径（默认 benchmarks/latency_report.md；测试用临时路径避免覆盖正式报告）")
    args = ap.parse_args()
    if args.n < 3:
        raise SystemExit("--n 至少为 3（第 1 次为预热，不计入统计）")

    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    warm_ms = run_once(fixture)  # 预热：import/数据加载
    samples = [run_once(fixture) for _ in range(args.n)]

    p50 = statistics.median(samples)
    p95 = sorted(samples)[min(len(samples) - 1, int(0.95 * len(samples)))]
    env = {
        "CPU": platform.processor() or platform.machine(),
        "架构": platform.machine(),
        "Python": platform.python_version(),
        "操作系统": platform.platform(),
    }

    lines = [
        "# C7 效率基准：本地全链路延迟",
        "",
        "> 生成：`python scripts/benchmark_latency.py --n %d`" % args.n,
        "> 链路：Claim → 验证 → 工程归一化 → 经济映射 → 因果批判 → 财务三情景",
        "> 模式：`local_only=True`（无 LLM、无网络），与 `python app.py` Demo 同链路",
        "",
        "## 结果",
        "",
        "| 指标 | 值 |",
        "|---|---|",
        f"| 样本量 N | {args.n}（另计预热 1 次 {warm_ms:.1f} ms） |",
        f"| p50 | **{p50:.1f} ms** |",
        f"| p95 | {p95:.1f} ms |",
        f"| min | {min(samples):.1f} ms |",
        f"| max | {max(samples):.1f} ms |",
        f"| mean ± stdev | {statistics.fmean(samples):.1f} ± {statistics.stdev(samples):.1f} ms |",
        "",
        "## 环境",
        "",
        "| 项 | 值 |",
        "|---|---|",
        *[f"| {k} | {v} |" for k, v in env.items()],
        "",
        "## 口径说明",
        "",
        "- 测量的是本地确定性规则链路的端到端延迟；接入 LLM 后的延迟取决于",
        "  API 响应时间，不在本基准范围（如实标注，不混淆两种口径）。",
        "- 单进程串行测量，未模拟并发；如需并发基准需另行设计。",
        "- 该数字对应项目书 05 章 [C7] 效率实测口径（`local_only` 全链路）。",
    ]
    out_path = Path(args.out)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"latency report -> {out_path}")
    print(f"p50={p50:.1f}ms p95={p95:.1f}ms min={min(samples):.1f}ms max={max(samples):.1f}ms")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()

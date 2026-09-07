# C7 效率基准：本地全链路延迟

> 生成：`python scripts/benchmark_latency.py --n 3`
> 链路：Claim → 验证 → 工程归一化 → 经济映射 → 因果批判 → 财务三情景
> 模式：`local_only=True`（无 LLM、无网络），与 `python app.py` Demo 同链路

## 结果

| 指标 | 值 |
|---|---|
| 样本量 N | 3（另计预热 1 次 5.6 ms） |
| p50 | **4.2 ms** |
| p95 | 4.3 ms |
| min | 4.1 ms |
| max | 4.3 ms |
| mean ± stdev | 4.2 ± 0.1 ms |

## 环境

| 项 | 值 |
|---|---|
| CPU | AMD64 Family 26 Model 68 Stepping 0, AuthenticAMD |
| 架构 | AMD64 |
| Python | 3.12.10 |
| 操作系统 | Windows-11-10.0.26200-SP0 |

## 口径说明

- 测量的是本地确定性规则链路的端到端延迟；接入 LLM 后的延迟取决于
  API 响应时间，不在本基准范围（如实标注，不混淆两种口径）。
- 单进程串行测量，未模拟并发；如需并发基准需另行设计。
- 该数字对应项目书 05 章 [C7] 效率实测口径（`local_only` 全链路）。

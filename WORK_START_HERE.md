# Claim2Value 研究工作台

面向机器人产业链研究的本地工作台。三个任务：**观点审查**（把企业表述拆成待检查条件，在材料中检索支持与反证）、**财务整理**（从年报提取财务候选，核验后做两期盈利变化）、**策略回测**（先体检行情数据，再算净值、回撤与同费率基准）。

## 怎么开始

```bash
# Windows
start_harness.bat
```

```bash
# Linux / macOS
bash start_harness.sh
```

浏览器打开 http://127.0.0.1:8510 。默认无需账号；财务核验、数据体检与回测都是本地规则，**不需要模型密钥**。只有候选整理与观点检索要按需连接自备的模型接口。

## 当前状态

- 已核对案例：绿的谐波 2024 年年度报告（13 页公开披露文本）。
- 财务提取有逐字引用锚定与报表口径校验；同一份原件两轮对比的收据见 `05_技术证据/本轮口径修复_20261012/`。
- Windows 11 一键启动已实际验收；Linux 未在真机验证。
- 真人试用、CSMAR 正式字段定义、四条待证技术声明仍待补齐。

## 文档与入口

- 产品操作与教程：[docs/harness/getting_started.md](docs/harness/getting_started.md)、[docs/harness/industry_workflow.md](docs/harness/industry_workflow.md)
- 设计说明汇总：[docs/harness/design-notes.md](docs/harness/design-notes.md)
- 数据说明汇总：[docs/harness/data-notes.md](docs/harness/data-notes.md)
- 历次开发记录：[docs/CHANGELOG.md](docs/CHANGELOG.md)
- 初赛与旧版 Demo 归档：`legacy/`

商业数据库原始导出、校园账号与密钥留在授权私有目录，不进入本仓库与提交包。

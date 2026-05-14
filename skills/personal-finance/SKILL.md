---
name: personal-finance
description: 个人财务分析，专为钱迹(QianJi)等记账APP导出的CSV设计。两级分析体系：①快速数据概览（analyze.py十段分析，五层递进：结构→效率→行为→预测→诊断）②深度AI洞察（8模块框架：行为归因、压力测试、机会成本、价值观对齐、反事实推演）。纯stdlib零依赖+HTML模板分离。触发场景：钱迹、记账分析、账单分析、个人财务、消费分析、月度支出、省钱建议、理财、QianJi、CSV账单——即使文件不叫"钱迹"，只要是收支流水CSV就应触发。用户说"深度分析"/"深入分析"/"全面分析"/"8模块"时，启用深度AI洞察模式。
version: 3.5.0
author: User
license: MIT
tags:
  - finance
  - personal-finance
  - budgeting
  - csv-analysis
  - qianji
  - expense-tracking
agents:
  - claude-code
  - codex-cli
  - cursor
  - openclaw
---

# 个人财务分析 (Personal Finance)

钱迹等记账APP导出的CSV账单一键分析。自动识别列名，零依赖运行。

## 两级分析体系

```
用户说"分析账单"
  └─ 默认 → analyze.py 十段数据概览（秒级）
        ├─ 收支结构、吃喝拆解、现金流、消费画像、预测、仪表盘
        └─ 发现异常/关注特定方向后 → 可进入深度模式

用户说"深度分析"/"全面分析"/"深入分析"
  └─ AI深度洞察 → analyze.py 数据 + 8模块框架（分钟级）
        ├─ 行为归因、心理动机、压力测试、机会成本
        ├─ 价值观对齐、反事实推演、决策复盘
        └─ 输出：8模块完整报告 + 优先级行动清单
```

**数据层和洞察层是上下游关系**：脚本负责精确计算，AI 负责因果推理。决不要跳过数据层直接做深度分析。

## Quick Start

**默认模式 — 数据概览：**
```bash
python3 <skill-dir>/scripts/analyze.py <CSV文件路径>
```

**深度模式 — AI 洞察报告：**
```bash
python3 <skill-dir>/scripts/analyze.py <CSV文件路径>
# → 获取全部数据后 → 读取 references/deep-analysis-prompt.md → 按 8 模块输出深度报告
```

**HTML 报告：**
```bash
python3 <skill-dir>/scripts/analyze.py <CSV文件路径> --html 报告.html
```

## Rules

**数据层（analyze.py）：**
- 始终用脚本分析，不要自己写 inline Python 重新实现
- 用简洁中文呈现结果，突出异常和趋势，不堆砌数字
- 目录下有多个CSV时，先问用户分析哪个
- 单笔超过月均收入10%的支出，主动标记为异常
- 订阅月均超过收入5%时，给出精简建议
- EOF（文件末尾）前确保脚本输出完整，不要截断

**洞察层（8模块深度分析）：**
- 🔴 必须先运行 analyze.py 获取完整数据，再加载 `references/deep-analysis-prompt.md`
- 🔴 8 个模块必须全部覆盖，每个模块至少 3 个子节，严禁跳过或缩写
- 🔴 报告不少于 300 行，每个模块至少 1 个数据表格 + 1 个计算过程
- 每个结论必须绑定账本中的具体数字，不只列数字，还要说"这意味着什么"
- 深度分析时可直接读取 CSV 原始数据获取交易明细（如具体商品名、完整备注、单笔记录），补充 `analyze.py` 聚合输出未覆盖的细节
- 语气：锐利但不羞辱，质疑但不贬低。数据是你的武器，人身攻击不是。指出问题时用"你的账单显示…"而非"你是…"
- 报告结构：核心洞察摘要 → 8 模块正文 → 优先级行动清单（5件事，每件有数字有动作有截止时间）
- 反事实推演统一参数：年化 8%、20年/30年

## Reference Files

按需加载，不占用基础上下文：

| 文件 | 何时读取 | 内容 |
|------|---------|------|
| `references/methodology.md` | 需要理解分析框架或模块含义时 | 五层递进方法论 + 十段模块详解 + HTML 报告说明 |
| `references/deep-analysis-prompt.md` | 用户要求深度分析时 | 8 模块深度分析框架，含强制深度要求和收官检查清单 |
| `references/usage-guide.md` | 遇到列名不匹配、参数疑问或场景不确定时 | 列名自动匹配表 + 常见场景速查 + 标准参数 |

# rsi-automation-playbook

RSI 自动化分级与治理技能：给任务打 AL0-AL5 分级、按验证层级决定能自动化到哪一层、拆开生成与评判、规模化前上双层监控、盯斜率不盯绝对值。

一句话：**AI 研发的执行环节已被 AI 接管，人类剩下的稀缺能力收缩到两件事——品味（选什么问题）与裁判（判断做得好不好）。**

## 数据底座

- Anthropic 2026-08：Claude 主导（AL4）26% 研发工作，协作及以上 >90%，>80% 合入代码由 Claude 撰写
- 斜率：AL4 占比 3月 1% → 8月 26%（指数前段，非稳态）
- AL5（完全自主）全行业为零——卡点在"研究方向设定"（品味）
- arXiv:2607.07663 综述：1,250 篇（2024–2026），有界 vs 开放 RSI 分界

## 解决什么

| 痛点 | 本技能的做法 |
|---|---|
| 不知道一个任务该交给 AI 到什么程度 | AL 分级 + "还频繁插手=没到 AL4"判据 |
| 自动化后结果没法判好坏 | 验证层级门槛：无机器客观验收（formal/execution）不得 AL4+ 闭环 |
| 同一模型又写又评，越评越自信 | 拆开生成与评判：交叉模型/外部 ground truth/可检验断言 |
| Agent 规模化后罕见失误变常态 | 双层监控：不可逆事前拦截 + 可逆事后抽审 1-2% + 三指标（覆盖率/审查延迟/升级率） |
| 投入判断看绝对值错过窗口 | 盯斜率：1%→26% 型曲线的能力现在改工作流 |

## 安装

复制本目录到 `~/.agents/skills/`（或你的 Skill 加载路径）即可。

## 自检

```bash
python scripts/validate.py tests/sample_good.json   # 必须 exit 0
python scripts/validate.py tests/sample_bad.json    # 必须 exit 1
```

## 结构

```
SKILL.md                              工作流入口（一条主线 + 7 步流程 + 6 条硬规则）
references/al-scale.md                AL0-AL5 定义 + Anthropic 2026-08 数据 + 分级判据
references/verification-hierarchy.md  四层验证层级 + 有界/开放 RSI + 失败模式解释
references/monitoring.md              双层监控三指标 + 30k Agent 运行数据 + 最小可行动作
references/gotchas.md                 自我确认循环/罕见事件常态化/59%vs35% 对冲/坑位清单
scripts/validate.py                   自动化计划六维校验器（exit 0/1/2）
tests/sample_good.json                通过基准
tests/sample_bad.json                 拦截基准（承诺AL5/降级/自产自销/无事前拦截…）
docs/methodology.md                   方法论全文（奥卡姆剃刀提炼 + 11 个分点 + 6 条行动指南）
```

# Move Decider（移动决策引擎 · 上京包）

日本国内移动的决策模型：输入个人档案＋一趟行程，枚举出行策略，用确定性规则算清每条策略的现金、时间与风险总账，再由解释层给出推荐与取舍说明。未知项明示，估算不冒充实价。

## 结构

- `engine.py` — 确定性算账层（数字只出自 `data/prices.json`）＋风险规则
- `explainer.py` — 解释层：有 `NEBIUS_API_KEY` 时走 Nebius Token Factory 调 Nemotron；无 key 时 MOCK（明确标注），输出同 schema
- `data/prices.json` — 价格带（每条带 source / as_of / confidence）
- `cases/` — 行程输入：`tokyo_nov.json`（2026-11-01→06 真实行程回放）、`snow_jan.json`（雪季变体）、`budget.json`（预算优先变体）
- `demo/index.html` — 单文件演示页：拖动时间单价、切换季节与优先级，推荐实时变化
- `BUSINESS_MODEL.md` — 商业模型；`REPORT.md` — 迭代与自检报告

## 运行

```bash
python3 engine.py cases/tokyo_nov.json          # 策略对比表
python3 explainer.py cases/tokyo_nov.json       # 解释层输出（无 key 时为 MOCK）
# 演示页：直接用浏览器打开 demo/index.html
```

## 接入真实模型（用户本人操作）

在 Nebius Token Factory 领取额度并生成 API key 后：`export NEBIUS_API_KEY=...` 再运行 `explainer.py` 即自动切换；调用失败会回落 MOCK 并在 unknowns 中如实标注。

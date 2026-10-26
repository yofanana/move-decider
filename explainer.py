#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
解释层。接口：explain(evaluation: dict) -> dict（固定 schema）。
- 环境变量 NEBIUS_API_KEY 存在时：走 Nebius Token Factory（OpenAI 兼容接口）调 Nemotron 生成解释。
- 不存在时：MOCK 模式——用确定性模板从算账结果生成同 schema 输出，并明确标注 mode=mock。
铁律：解释层只能引用 evaluation 里已有的数字；缺失数据进 unknowns，不许编造。
"""
import json, os, urllib.request

SCHEMA_KEYS = ["mode", "recommended_strategy", "headline", "tradeoffs",
               "hidden_assumptions", "sensitivity", "unknowns"]

def _mock_explain(ev):
    rec = next(r for r in ev["strategies"] if r["id"] == ev["recommendation"])
    cheapest = min(ev["strategies"], key=lambda r: r["money_total"])
    fastest = min(ev["strategies"], key=lambda r: r["elapsed_hours"])
    tradeoffs = [f'{r["id"]} {r["name"]}：现金 ¥{r["money_total"]:,}、往返 {r["elapsed_hours"]} 小时、风险 {r["risk"]["level"]}——{r["blurb"]}'
                 for r in ev["strategies"]]
    hidden = [
        "默认这趟中间不用车（车只服务首尾两天）——若临时需要用车，S3/S6 的灵活性损失要另计",
        "各策略住宿按同一家横滨胶囊会员价计算；若改住田町附近，住宿带会整体抬高（此前调研商务酒店4晚 ¥51,100 起）",
        "价格为 2026-10-24 口径的价格带，出发前需复核 estimate 项",
    ]
    return {
        "mode": "mock",
        "recommended_strategy": rec["id"],
        "headline": f'推荐 {rec["id"]} {rec["name"]}：现金 ¥{rec["money_total"]:,}、往返 {rec["elapsed_hours"]} 小时；'
                    f'现金最低是 {cheapest["id"]}（¥{cheapest["money_total"]:,}），最快是 {fastest["id"]}（往返 {fastest["elapsed_hours"]} 小时）',
        "tradeoffs": tradeoffs,
        "hidden_assumptions": hidden,
        "sensitivity": ev["sensitivity"]["note"],
        "unknowns": ev["unknowns"],
    }

def _nemotron_explain(ev):
    key = os.environ["NEBIUS_API_KEY"]
    prompt = (
        "你是出行决策解释员。只能使用下列 JSON 中已有的数字与事实，禁止编造价格；"
        "用中文输出一个 JSON 对象，字段为 recommended_strategy, headline, tradeoffs(数组), "
        "hidden_assumptions(数组), sensitivity, unknowns(数组)。评价数据：\n"
        + json.dumps(ev, ensure_ascii=False)
    )
    body = json.dumps({
        "model": "nvidia/nemotron-3-super-120b-a12b",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.tokenfactory.nebius.com/v1/chat/completions",
        data=body, headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as resp:
        data = json.load(resp)
    out = json.loads(data["choices"][0]["message"]["content"])
    out["mode"] = "nemotron"
    return out

def explain(ev):
    if os.environ.get("NEBIUS_API_KEY"):
        try:
            return _nemotron_explain(ev)
        except Exception as e:  # 接口不通则回落到 MOCK 并如实标注原因
            out = _mock_explain(ev)
            out["mode"] = "mock (nemotron 调用失败回落)"
            out["unknowns"] = [f"Nemotron 调用失败：{e}"] + out["unknowns"]
            return out
    return _mock_explain(ev)

if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from engine import evaluate
    case = json.load(open(sys.argv[1], encoding="utf-8"))
    print(json.dumps(explain(evaluate(case)), ensure_ascii=False, indent=2))

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
移动决策引擎 v2（2026-10-24）——确定性算账层。
理论：一般化费用（现金＋时间×时间价值）＋随机效用的属性表＋旅行的正效用（享受值）。
铁律：数字只能出自 data/prices.json；解释层（explainer.py）无权改数字。
时间模型：门到门分段——驾驶×coef_drive、休息×coef_rest、乘车×coef_ride（用户档案校准）。
用法：python3 engine.py cases/tokyo_nov.json [--json out.json]
"""
import json, sys, os

HERE = os.path.dirname(os.path.abspath(__file__))
PRICES = json.load(open(os.path.join(HERE, "data", "prices.json"), encoding="utf-8"))["items"]

def amt(key):
    return PRICES[key]["amount"]

DEFAULT_COEF = {"drive": 0.5, "rest": 1.0, "ride": 1.0}  # 驾驶半价＝播客使路上时间有正效用（用户校准）

# ---- 东京走廊（上京包）：单程分段小时 drive/rest/ride（ride 含车站与衔接） ----
def tokyo_strategies(case):
    nights = case["nights"]
    park_days = nights + 1
    hotel_per_night = amt("hotel_yokohama_capsule_5n_member") / 5
    access = case.get("station_access_min", 25) / 60  # 自宅→越后汤泽站 单程驾驶（用户实测25分钟）
    return [
        {"id": "S1", "name": "全程自驾＋高速",
         "cost_items": [("fuel_rt_expressway", 1), ("toll_rt_keicar_etc_yuzawa_yokohama", 1),
                        ("parking_akippa_kibogaoka_6d", 1), ("hotel_yokohama_capsule_5n_member", 1)],
         "seg": {"drive": 3.8, "rest": 0.8, "ride": 0.0}, "enjoy": True,
         "comfort": "中", "convenience": "高",
         "blurb": "最快到达的开车法，钱花在通行费上"},
        {"id": "S2", "name": "全程自驾＋国道",
         "cost_items": [("fuel_rt_national_roads", 1),
                        ("parking_akippa_kibogaoka_6d", 1), ("hotel_yokohama_capsule_5n_member", 1)],
         "seg": {"drive": 5.5, "rest": 1.5, "ride": 0.0}, "enjoy": True,
         "comfort": "中", "convenience": "高",
         "blurb": "现金最省的开车法，时间花在路上（本案例的实际选择）"},
        {"id": "S3", "name": "新干线直达",
         "cost_items": [("shinkansen_yuzawa_tokyo_oneway", 2), ("hotel_yokohama_capsule_5n_member", 1)],
         "seg": {"drive": access, "rest": 0.0, "ride": 1.7}, "enjoy": False,
         "comfort": "高", "convenience": "中",
         "blurb": "不带车：车停汤泽站（11月免费期¥0），行李可宅配"},
        {"id": "S4", "name": "自驾到高崎换新干线",
         "cost_items": [("fuel_oneway_to_takasaki", 2), ("parking_takasaki_area_per_day", park_days),
                        ("shinkansen_takasaki_tokyo_oneway", 2), ("hotel_yokohama_capsule_5n_member", 1)],
         "seg": {"drive": 1.7, "rest": 0.0, "ride": 1.2}, "enjoy": False,
         "comfort": "中高", "convenience": "中高",
         "blurb": "只开前段山路，停车便宜，返程有车"},
        {"id": "S5", "name": "国道自驾＋混合车中泊（3晚酒店）",
         "cost_items": [("fuel_rt_national_roads", 1), ("parking_akippa_kibogaoka_6d", 1)],
         "hotel_override": round(hotel_per_night * 3),
         "seg": {"drive": 5.5, "rest": 1.5, "ride": 0.0}, "enjoy": True,
         "comfort": "低", "convenience": "高",
         "blurb": "现金最低：2晚睡车里，舒适与合规停车点未核实"},
        {"id": "S6", "name": "高速巴士往返",
         "cost_items": [("highway_bus_yuzawa_tokyo_oneway", 2), ("hotel_yokohama_capsule_5n_member", 1)],
         "seg": {"drive": access, "rest": 0.0, "ride": 3.8}, "enjoy": False,
         "comfort": "中", "convenience": "中低",
         "blurb": "不用开车也不贵，但班次少、时刻绑死"},
    ]

def tokyo_risk(case, sid):
    base = {
        "S1": ("yellow", "关越道冬季有チェーン規制与降雪延误可能"),
        "S2": ("yellow", "单程约7小时（含休息），疲劳驾驶是主要风险"),
        "S3": ("green", "新干线冬季可靠性最高"),
        "S4": ("yellow", "前段山路（国道17号/三国峠）冬季积雪"),
        "S5": ("yellow", "长途疲劳＋车中泊舒适度；11月夜间低温"),
        "S6": ("yellow", "班次少，取消时替代选项有限"),
    }
    level, why = base[sid]
    if case["season"] == "winter":
        winter = {
            "S1": ("yellow", "关越道冬季チェーン規制可能；高速仍比国道可控"),
            "S2": ("red", "雪季国道三国峠积雪＋长途疲劳——否决级风险"),
            "S3": ("green", "新干线冬季可靠性最高"),
            "S4": ("yellow", "前段山路积雪，但暴露距离短"),
            "S5": ("red", "雪季严寒车中泊＋长途疲劳——否决级风险"),
            "S6": ("yellow", "大雪时巴士可能停运，需备选"),
        }
        level, why = winter[sid]
    return {"level": level, "reason": why}

# ---- 前桥走廊（考试当天往返包，价格全部 estimate，考场确定后复核） ----
def maebashi_strategies(case):
    access = case.get("station_access_min", 25) / 60
    return [
        {"id": "M1", "name": "全程自驾＋高速（关越道）",
         "cost_items": [("fuel_rt_maebashi_expressway", 1), ("toll_rt_keicar_yuzawa_maebashi", 1),
                        ("parking_maebashi_day", 1)],
         "seg": {"drive": 1.6, "rest": 0.0, "ride": 0.0}, "enjoy": True,
         "comfort": "中", "convenience": "高",
         "blurb": "门到门最可控，考试日不依赖班次"},
        {"id": "M2", "name": "全程自驾＋国道17号（三国峠）",
         "cost_items": [("fuel_rt_maebashi_national", 1), ("parking_maebashi_day", 1)],
         "seg": {"drive": 2.6, "rest": 0.2, "ride": 0.0}, "enjoy": True,
         "comfort": "中低", "convenience": "高",
         "blurb": "现金最低，但11月中旬三国峠有初雪与路面冻结风险"},
        {"id": "M3", "name": "新干线＋两毛线",
         "cost_items": [("shinkansen_yuzawa_takasaki_oneway", 2), ("jr_ryomo_takasaki_maebashi_oneway", 2)],
         "seg": {"drive": access, "rest": 0.0, "ride": 1.2}, "enjoy": False,
         "comfort": "高", "convenience": "中",
         "blurb": "坐着到，精力留给考试；受换乘时刻约束，前桥站到考场另计"},
        {"id": "M4", "name": "自驾到高崎＋两毛线",
         "cost_items": [("fuel_oneway_to_takasaki", 2), ("parking_takasaki_area_per_day", 1),
                        ("jr_ryomo_takasaki_maebashi_oneway", 2)],
         "seg": {"drive": 1.7, "rest": 0.0, "ride": 0.5}, "enjoy": False,
         "comfort": "中高", "convenience": "中高",
         "blurb": "山路自己开、平原段坐车，返程时间自由"},
    ]

def maebashi_risk(case, sid):
    base = {
        "M1": ("green", "高速路况可控，注意关越道周末返程拥堵"),
        "M2": ("yellow", "11月中旬三国峠初雪/冻结可能，考试日不容有失"),
        "M3": ("green", "班次固定，提前一班出发即可对冲"),
        "M4": ("yellow", "前段山路同M2风险，但距离短于全程国道"),
    }
    level, why = base[sid]
    return {"level": level, "reason": why}

CORRIDORS = {
    "tokyo": (tokyo_strategies, tokyo_risk,
              ["高速通行费未计深夜/休日割引（ETC深夜3割需0-4时通行，满足时S1可再降约3,000量级）",
               "新干线未计えきねっとトクだ値等提前折扣（有货时S3/S4可再降）",
               "横滨周边合法车中泊点未核实（影响S5可行性）",
               "行李宅配（约¥4,500往返）为可选附加项，未计入S3/S6",
               "市内交通与餐饮未计入（各策略近似相同）"]),
    "maebashi": (maebashi_strategies, maebashi_risk,
                 ["前桥包价格全部为 estimate：考场（2026-11-15 赁贷资格检定）确定后须逐项复核",
                  "前桥站/考场周边的接驳与停车未核实",
                  "三国峠当日路况须出发前以官方道路信息确认"]),
}

def evaluate(case):
    tv = case["time_value_jpy_per_hour"]
    coef = {**DEFAULT_COEF, **case.get("time_use_coefficients", {})}
    enjoyment = case.get("enjoyment_jpy", 0)
    mk, rk, extra_unknowns = CORRIDORS[case.get("corridor", "tokyo")]
    results, used_keys = [], set()
    for s in mk(case):
        total = s.get("hotel_override", 0)
        breakdown = []
        if "hotel_override" in s:
            breakdown.append({"item": "酒店3晚（按5晚会员价折算）", "amount": s["hotel_override"], "confidence": "verified"})
        for key, mult in s["cost_items"]:
            a = amt(key) * mult
            total += a
            breakdown.append({"item": key, "amount": a, "confidence": PRICES[key]["confidence"]})
            used_keys.add(key)
        seg_rt = {k: round(v * 2, 2) for k, v in s["seg"].items()}
        elapsed = round(sum(seg_rt.values()), 2)
        equiv_raw = sum(seg_rt[k] * coef[k] for k in seg_rt)
        equiv = round(equiv_raw, 2)
        time_cost = round(equiv_raw * tv)
        enjoy_credit = enjoyment if s.get("enjoy") else 0
        r = rk(case, s["id"])
        results.append({
            "id": s["id"], "name": s["name"], "blurb": s["blurb"],
            "money_total": total, "breakdown": breakdown,
            "segments_rt": seg_rt, "elapsed_hours": elapsed, "equiv_hours": equiv,
            "time_cost": time_cost, "enjoyment_credit": enjoy_credit,
            "effective_total": total + time_cost - enjoy_credit,
            "comfort": s["comfort"], "convenience": s["convenience"],
            "risk": r,
        })
    pool = [r for r in results if r["risk"]["level"] != "red"] or results
    if case.get("priority") == "money":
        rec = min(pool, key=lambda r: r["money_total"])
    else:
        rec = min(pool, key=lambda r: r["effective_total"])
    for r in results:
        r["recommended"] = (r["id"] == rec["id"])
    # 敏感性①：经典款 S1 vs S2 的时间单价临界点（若走廊含此二者）
    sens = {}
    ids = {r["id"] for r in results}
    if {"S1", "S2"} <= ids:
        s1 = next(r for r in results if r["id"] == "S1"); s2 = next(r for r in results if r["id"] == "S2")
        saved = s2["equiv_hours"] - s1["equiv_hours"]
        if saved > 0:
            sens["breakeven_time_value_s1_vs_s2"] = round((s1["money_total"] - s2["money_total"]) / saved)
    # 敏感性②：用户实际选择（S2）翻转为推荐所需的享受值门槛
    if "S2" in ids and rec["id"] != "S2":
        s2 = next(r for r in results if r["id"] == "S2")
        sens["enjoyment_threshold_for_s2"] = (s2["money_total"] + s2["time_cost"]) - rec["effective_total"]
    unknowns = [f"{k}：{PRICES[k]['source']}" for k in sorted(used_keys) if PRICES[k]["confidence"] != "verified"]
    unknowns += extra_unknowns
    return {"case": case["case_id"], "title": case["title"], "corridor": case.get("corridor", "tokyo"),
            "time_value": tv, "coefficients": coef, "enjoyment_jpy": enjoyment,
            "strategies": results, "recommendation": rec["id"],
            "sensitivity": sens, "unknowns": unknowns}

if __name__ == "__main__":
    case = json.load(open(sys.argv[1], encoding="utf-8"))
    out = evaluate(case)
    if "--json" in sys.argv:
        path = sys.argv[sys.argv.index("--json") + 1]
        json.dump(out, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    for r in out["strategies"]:
        star = " ★推荐" if r["recommended"] else ""
        print(f'{r["id"]} {r["name"]}: 现金 ¥{r["money_total"]:,} / 门到门 {r["elapsed_hours"]}h（折算 {r["equiv_hours"]}h）/ '
              f'时间成本 ¥{r["time_cost"]:,} / 享受值 -¥{r["enjoyment_credit"]:,} / 有效总成本 ¥{r["effective_total"]:,} / '
              f'舒适 {r["comfort"]} / 便利 {r["convenience"]} / 风险 {r["risk"]["level"]}{star}')
    print("敏感性:", json.dumps(out["sensitivity"], ensure_ascii=False))

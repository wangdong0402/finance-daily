import requests
import json
import os
import time
from datetime import datetime

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://data.eastmoney.com/"
}
UT = "bd1d9ddb04089700cf9c27f6f7426281"
RANK_URL = "https://push2.eastmoney.com/api/qt/clist/get"
HIS_URL = "https://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get"

# 候选板块池大小（50个行业取前30）
CANDIDATE_POOL = 30
# 请求间隔（秒），东方财富默认最小间隔1.0秒
REQUEST_INTERVAL = 1.2
# 重试次数
MAX_RETRIES = 3


def request_with_retry(url, params, headers, timeout=15):
    """带重试的请求封装"""
    for attempt in range(MAX_RETRIES):
        try:
            res = requests.get(url, params=params, headers=headers, timeout=timeout)
            res.raise_for_status()
            return res
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                wait = (attempt + 1) * 2
                print(f"[重试] 第{attempt+1}次失败，等待{wait}秒后重试: {e}")
                time.sleep(wait)
            else:
                print(f"[失败] 重试{MAX_RETRIES}次后仍失败: {e}")
                return None


def fetch_rank(indicator, po, page_size=100):
    """获取板块资金流排名，indicator支持today/3day/5day/10day"""
    params = {
        "pn": 1, "pz": page_size, "np": 1, "fltt": 2, "invt": 2,
        "fs": "m:90+t:2", "fields": "f12,f14,f3,f62",
        "ut": UT, "fid": "f62", "po": po, "indicator": indicator
    }
    res = request_with_retry(RANK_URL, params, HEADERS)
    if not res:
        return []
    try:
        data = res.json()
        items = []
        if data.get("data") and data["data"].get("diff"):
            for item in data["data"]["diff"]:
                items.append({
                    "name": item.get("f14", ""),
                    "code": item.get("f12", ""),
                    "change": item.get("f3", 0),
                    "main_net": round(item.get("f62", 0) / 100000000, 2)
                })
        return items
    except Exception as e:
        print(f"[警告] 排行接口 {indicator} po={po} 解析异常: {e}")
        return []


def fetch_sector_history(code, days=60):
    """获取单个行业板块最近days个交易日的主力净流入序列，单位统一为亿元"""
    secid = f"90.{code}"
    params = {
        "secid": secid,
        "fields1": "f1,f2,f3,f7",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65",
        "klt": "101",
        "lmt": str(days + 10),
        "ut": UT
    }
    res = request_with_retry(HIS_URL, params, HEADERS)
    if not res:
        return None
    try:
        data = res.json()
        klines = data.get("data", {}).get("klines", [])
        if not klines:
            return None
        flows = []
        for line in klines[-days:]:
            parts = line.split(",")
            if len(parts) >= 2:
                try:
                    flows.append(float(parts[1]))
                except ValueError:
                    continue
        if not flows:
            return None
        return {
            "name": data.get("data", {}).get("name", ""),
            "code": code,
            "main_net": round(sum(flows) / 100000000, 2),
            "days": len(flows)
        }
    except Exception as e:
        print(f"[警告] 历史接口 {code} 异常: {e}")
        return None


def build_period_ranking(candidates, days):
    """对候选板块拉取历史并累加"""
    results = []
    for i, c in enumerate(candidates):
        hist = fetch_sector_history(c["code"], days=days)
        if hist and hist["main_net"] != 0:
            results.append(hist)
        if (i + 1) % 5 == 0:
            print(f"    已处理 {i+1}/{len(candidates)} 个候选板块...")
        time.sleep(REQUEST_INTERVAL)
    results.sort(key=lambda x: x["main_net"], reverse=True)
    return results


def main():
    sentiment_data = {
        "updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "periods": {}
    }

    # 5日：直接使用排行接口（5day是原生参数）
    print("[信息] 抓取 5日 排行...")
    inflow_5d = fetch_rank("5day", 1, 10)
    time.sleep(REQUEST_INTERVAL)
    outflow_5d = fetch_rank("5day", 0, 10)
    sentiment_data["periods"]["5d"] = {"inflow": inflow_5d, "outflow": outflow_5d}
    print(f"  5日：流入 {len(inflow_5d)} 条，流出 {len(outflow_5d)} 条")

    # 20日 / 60日：用10日排行取候选，再累加历史
    print("[信息] 抓取 10日 候选池（用于20/60日累加）...")
    candidates_in = fetch_rank("10day", 1, CANDIDATE_POOL)
    time.sleep(REQUEST_INTERVAL)
    candidates_out = fetch_rank("10day", 0, CANDIDATE_POOL)
    all_candidates = candidates_in + candidates_out
    print(f"  候选池共 {len(all_candidates)} 个板块")

    for days, label in [(20, "20d"), (60, "60d")]:
        print(f"[信息] 计算 {days} 日累计排行（候选 {len(all_candidates)} 个）...")
        full_ranking = build_period_ranking(all_candidates, days)
        inflow = full_ranking[:10]
        outflow = sorted(full_ranking, key=lambda x: x["main_net"])[:10]
        sentiment_data["periods"][label] = {"inflow": inflow, "outflow": outflow}
        print(f"  {days}日：流入 {len(inflow)} 条，流出 {len(outflow)} 条")

    os.makedirs("data", exist_ok=True)
    with open("data/sentiment.json", "w", encoding="utf-8") as f:
        json.dump(sentiment_data, f, ensure_ascii=False, indent=2)
    print("情绪数据保存完成。")


if __name__ == "__main__":
    main()

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

def fetch_rank(indicator, po):
    """获取行业资金流排名，indicator仅支持5day/10day，po=1流入/0流出"""
    params = {
        "pn": 1, "pz": 10, "np": 1, "fltt": 2, "invt": 2,
        "fs": "m:90+t:2", "fields": "f12,f14,f3,f62",
        "ut": UT, "fid": "f62", "po": po, "indicator": indicator
    }
    try:
        # 加上较短的超时和单次请求
        res = requests.get(RANK_URL, params=params, headers=HEADERS, timeout=10)
        res.raise_for_status()
        data = res.json()
        items = []
        if data.get("data") and data["data"].get("diff"):
            for item in data["data"]["diff"]:
                items.append({
                    "name": item.get("f14", ""),
                    "change": item.get("f3", 0),
                    "main_net": round(item.get("f62", 0) / 100000000, 2)
                })
        return items
    except Exception as e:
        print(f"[警告] 排行接口 {indicator} po={po} 异常: {e}")
        return []

def main():
    sentiment_data = {
        "updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "periods": {}
    }

    # 抓取 10日 排行
    print("[信息] 抓取 10日 排行...")
    inflow_10d = fetch_rank("10day", 1)
    time.sleep(1.5)
    outflow_10d = fetch_rank("10day", 0)
    sentiment_data["periods"]["10d"] = {"inflow": inflow_10d, "outflow": outflow_10d}

    # 抓取 5日 排行
    print("[信息] 抓取 5日 排行...")
    time.sleep(1.5)
    inflow_5d = fetch_rank("5day", 1)
    time.sleep(1.5)
    outflow_5d = fetch_rank("5day", 0)
    sentiment_data["periods"]["5d"] = {"inflow": inflow_5d, "outflow": outflow_5d}

    os.makedirs("data", exist_ok=True)
    with open("data/sentiment.json", "w", encoding="utf-8") as f:
        json.dump(sentiment_data, f, ensure_ascii=False, indent=2)
    print("情绪数据保存完成。")

if __name__ == "__main__":
    main()

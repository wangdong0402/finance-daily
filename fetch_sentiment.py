import requests
import json
import os
from datetime import datetime

def fetch_market_sentiment():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://quote.eastmoney.com/"
    }

    sentiment_data = {
        "updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "panic_index": None,
        "suggested_position": None,
        "main_net_buy": 0.0,
        "sector_panic_top5": [],
        "market_theme": ""
    }

    # 1. 实时恐贪情绪 + 仓位建议（统一路径 + fn 参数 + GBK 解码）
    try:
        url = "https://push2delay.eastmoney.com/api/qt/stock/get"
        params = {"fn": "panicIndextrade"}
        res = requests.get(url, params=params, headers=headers, timeout=10)
        res.raise_for_status()
        data = json.loads(res.content.decode('gbk', errors='ignore'))
        raw = data.get("data")
        if isinstance(raw, dict):
            sentiment_data["panic_index"] = raw.get("panicIndex")
            sentiment_data["suggested_position"] = raw.get("suggestPosition")
        print(f"[信息] 恐贪指数接口返回成功")
    except Exception as e:
        print(f"[警告] 恐贪指数接口异常: {e}")

    # 2. 主力净买额（已成功，保持原样）
    try:
        url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
        params = {
            "reportName": "RPT_MRRKET_FINNETBUYAMT1Y",
            "pageSize": 1,
            "pageNumber": 1,
            "sortTypes": -1,
            "sortColumns": "TRADE_DATE"
        }
        res = requests.get(url, params=params, headers=headers, timeout=10)
        res.raise_for_status()
        data = res.json()
        if data.get("result") and data["result"].get("data"):
            item = data["result"]["data"][0]
            raw_val = item.get("NET_BUY_AMT", 0)
            sentiment_data["main_net_buy"] = round(raw_val / 100000000, 2)
        print(f"[信息] 主力净买额接口返回成功")
    except Exception as e:
        print(f"[警告] 主力净买额接口异常: {e}")

    # 3. 板块恐贪榜 Top5（统一路径 + fn 参数 + UTF-8）
    try:
        url = "https://push2delay.eastmoney.com/api/qt/stock/get"
        params = {"fn": "panicbklist"}
        res = requests.get(url, params=params, headers=headers, timeout=10)
        res.raise_for_status()
        data = res.json()
        if data.get("data"):
            sectors = data["data"]
            sectors_sorted = sorted(sectors, key=lambda x: x.get("panicValue", 100))[:5]
            for s in sectors_sorted:
                sentiment_data["sector_panic_top5"].append({
                    "name": s.get("bkName", ""),
                    "panic": s.get("panicValue", 0)
                })
        print(f"[信息] 板块恐贪榜接口返回成功")
    except Exception as e:
        print(f"[警告] 板块恐贪榜接口异常: {e}")

    # 4. 市场主线（统一路径 + fn 参数 + GBK 解码）
    try:
        url = "https://push2delay.eastmoney.com/api/qt/stock/get"
        params = {"fn": "panicMThemeList"}
        res = requests.get(url, params=params, headers=headers, timeout=10)
        res.raise_for_status()
        data = json.loads(res.content.decode('gbk', errors='ignore'))
        if data.get("data"):
            themes = [t.get("themeName", "") for t in data["data"][:3]]
            sentiment_data["market_theme"] = " / ".join([t for t in themes if t])
        print(f"[信息] 市场主线接口返回成功")
    except Exception as e:
        print(f"[警告] 市场主线接口异常: {e}")

    # 核心数据：只要恐贪指数或主力净买额有一个成功，就保存
    if sentiment_data["panic_index"] is None and sentiment_data["main_net_buy"] == 0.0:
        return None

    return sentiment_data

def main():
    data = fetch_market_sentiment()
    if data:
        os.makedirs("data", exist_ok=True)
        with open("data/sentiment.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"已保存情绪数据：恐贪={data['panic_index']}，主力净买={data['main_net_buy']} 亿")
    else:
        print("核心情绪数据（恐贪/主力净买）均未获取到，跳过保存。")

if __name__ == "__main__":
    main()

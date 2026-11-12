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

    # 1. 实时恐贪情绪 + 仓位建议 (补全 fields 参数)
    try:
        url = "https://push2delay.eastmoney.com/api/qt/stock/get"
        params = {
            "fn": "panicIndextrade",
            "fields": "f1,f2,f3,f4,f12,f13,f14,f104,f105,f106"
        }
        res = requests.get(url, params=params, headers=headers, timeout=10)
        res.raise_for_status()
        data = json.loads(res.content.decode('gbk', errors='ignore'))
        raw = data.get("data")
        if isinstance(raw, dict):
            sentiment_data["panic_index"] = raw.get("panicIndex") or raw.get("f104") or raw.get("f2")
            sentiment_data["suggested_position"] = raw.get("suggestPosition") or raw.get("f105")
        print(f"[信息] 恐贪指数接口成功返回")
    except Exception as e:
        print(f"[警告] 恐贪指数接口异常: {e}")

    # 2. 主力净买额 (补全 columns 参数)
    try:
        url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
        params = {
            "reportName": "RPT_MRRKET_FINNETBUYAMT1Y",
            "columns": "ALL",
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
            raw_val = item.get("NET_BUY_AMT") or item.get("NET_INFLOW") or 0
            sentiment_data["main_net_buy"] = round(raw_val / 100000000, 2)
        print(f"[信息] 主力净买额接口成功返回")
    except Exception as e:
        print(f"[警告] 主力净买额接口异常: {e}")

    # 3. 板块恐贪榜 Top5 (补全 fields 参数)
    try:
        url = "https://push2delay.eastmoney.com/api/qt/clist/get"
        params = {
            "fn": "panicbklist",
            "fields": "f12,f14,f2,f3,f104,f105"
        }
        res = requests.get(url, params=params, headers=headers, timeout=10)
        res.raise_for_status()
        data = res.json()
        if data.get("data") and isinstance(data["data"], dict) and data["data"].get("diff"):
            sectors = data["data"]["diff"]
            sectors_sorted = sorted(sectors, key=lambda x: x.get("f3", 100))[:5]
            for s in sectors_sorted:
                sentiment_data["sector_panic_top5"].append({
                    "name": s.get("f14", ""),
                    "panic": s.get("f3", 0)
                })
        print(f"[信息] 板块恐贪榜接口成功返回")
    except Exception as e:
        print(f"[警告] 板块恐贪榜接口异常: {e}")

    # 4. 市场主线 (补全 fields 参数)
    try:
        url = "https://push2delay.eastmoney.com/api/qt/stock/get"
        params = {
            "fn": "panicMThemeList",
            "fields": "f1,f2,f3,f4,f12,f13,f14"
        }
        res = requests.get(url, params=params, headers=headers, timeout=10)
        res.raise_for_status()
        data = json.loads(res.content.decode('gbk', errors='ignore'))
        if data.get("data") and isinstance(data["data"], list):
            themes = [t.get("f14", "") for t in data["data"][:3] if t.get("f14")]
            sentiment_data["market_theme"] = " / ".join(themes)
        print(f"[信息] 市场主线接口成功返回")
    except Exception as e:
        print(f"[警告] 市场主线接口异常: {e}")

    return sentiment_data

def main():
    data = fetch_market_sentiment()
    os.makedirs("data", exist_ok=True)
    with open("data/sentiment.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"情绪数据保存完成：恐贪={data['panic_index']}，主力净买={data['main_net_buy']} 亿")

if __name__ == "__main__":
    main()

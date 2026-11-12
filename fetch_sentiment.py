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
    
    has_data = False

    # 1. 实时恐贪情绪 + 仓位建议
    try:
        url = "https://push2delay.eastmoney.com/api/qt/stock/get"
        params = {"fn": "panicIndextrade"}
        res = requests.get(url, params=params, headers=headers, timeout=10)
        res.raise_for_status()
        data = json.loads(res.content.decode('gbk', errors='ignore'))
        print(f"--- 恐贪原始数据: {data} ---")  # 打印出来看结构
        
        raw = data.get("data")
        if isinstance(raw, dict):
            # 尝试抓取各种可能的字段名
            sentiment_data["panic_index"] = raw.get("panicIndex") or raw.get("value") or raw.get("f2")
            sentiment_data["suggested_position"] = raw.get("suggestPosition") or raw.get("position")
            has_data = True
    except Exception as e:
        print(f"[警告] 恐贪指数接口异常: {e}")

    # 2. 主力净买额
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
        print(f"--- 主力净买原始数据: {data} ---")
        
        if data.get("result") and data["result"].get("data"):
            item = data["result"]["data"][0]
            # 尝试抓取各种可能的字段名
            raw_val = item.get("NET_BUY_AMT") or item.get("NET_INFLOW") or 0
            sentiment_data["main_net_buy"] = round(raw_val / 100000000, 2)
            has_data = True
    except Exception as e:
        print(f"[警告] 主力净买额接口异常: {e}")

    # 3. 板块恐贪榜 Top5
    try:
        url = "https://push2delay.eastmoney.com/api/qt/stock/get"
        params = {"fn": "panicbklist"}
        res = requests.get(url, params=params, headers=headers, timeout=10)
        res.raise_for_status()
        data = res.json()
        print(f"--- 板块恐贪原始数据: {data} ---")
        
        if data.get("data") and isinstance(data["data"], list):
            sectors_sorted = sorted(data["data"], key=lambda x: x.get("panicValue", 100))[:5]
            for s in sectors_sorted:
                sentiment_data["sector_panic_top5"].append({
                    "name": s.get("bkName", ""),
                    "panic": s.get("panicValue", 0)
                })
            has_data = True
    except Exception as e:
        print(f"[警告] 板块恐贪榜接口异常: {e}")

    # 4. 市场主线
    try:
        url = "https://push2delay.eastmoney.com/api/qt/stock/get"
        params = {"fn": "panicMThemeList"}
        res = requests.get(url, params=params, headers=headers, timeout=10)
        res.raise_for_status()
        data = json.loads(res.content.decode('gbk', errors='ignore'))
        print(f"--- 市场主线原始数据: {data} ---")
        
        if data.get("data"):
            themes = [t.get("themeName", "") for t in data["data"][:3]]
            sentiment_data["market_theme"] = " / ".join([t for t in themes if t])
            has_data = True
    except Exception as e:
        print(f"[警告] 市场主线接口异常: {e}")

    # 只要有任何一部分成功获取，就允许保存
    if has_data:
        return sentiment_data
    return None

def main():
    data = fetch_market_sentiment()
    if data:
        os.makedirs("data", exist_ok=True)
        with open("data/sentiment.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"已保存情绪数据：恐贪={data['panic_index']}，主力净买={data['main_net_buy']} 亿")
    else:
        print("数据全空，跳过保存。")

if __name__ == "__main__":
    main()

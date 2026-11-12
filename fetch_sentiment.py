import requests
import json
import os
from datetime import datetime

def fetch_market_sentiment():
    # push2 系列接口需要携带公共 token 和伪装请求头
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://quote.eastmoney.com/"
    }
    # push2/push2delay 系列的公共 token
    UT = "bd1d9ddb04089700cf9c27f6f7426281"

    sentiment_data = {
        "updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "panic_index": None,
        "suggested_position": None,
        "main_net_buy": 0.0,
        "sector_panic_top5": [],
        "market_theme": ""
    }

    has_data = False

    # 1. 实时恐贪情绪 + 仓位建议 (panicIndextrade, GBK)
    try:
        url = "https://push2delay.eastmoney.com/api/qt/stock/get"
        params = {
            "fn": "panicIndextrade",
            "ut": UT
        }
        res = requests.get(url, params=params, headers=headers, timeout=10)
        res.raise_for_status()
        data = json.loads(res.content.decode('gbk', errors='ignore'))
        print(f"--- 恐贪原始数据: {data} ---")
        
        raw = data.get("data")
        if isinstance(raw, dict):
            # 字段 '5': 短线情绪(0~100), '9': 短线仓位(原始0~1)
            sentiment_data["panic_index"] = raw.get("5")
            pos = raw.get("9")
            if pos is not None:
                sentiment_data["suggested_position"] = round(float(pos) * 100, 2)
            has_data = True
    except Exception as e:
        print(f"[警告] 恐贪指数接口异常: {e}")

    # 2. 主力净买额 (RPT_MRRKET_FINNETBUYAMT1Y)
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
        print(f"--- 主力净买原始数据: {data} ---")
        
        if data.get("result") and data["result"].get("data"):
            item = data["result"]["data"][0]
            # 字段可能是 NET_BUY_AMT 或 f184
            raw_val = item.get("NET_BUY_AMT") or item.get("f184") or 0
            sentiment_data["main_net_buy"] = round(raw_val / 100000000, 2)
            has_data = True
    except Exception as e:
        print(f"[警告] 主力净买额接口异常: {e}")

    # 3. 板块恐贪榜 Top5 (panicbklist, UTF-8)
    try:
        url = "https://push2delay.eastmoney.com/api/qt/clist/get"
        params = {
            "fn": "panicbklist",
            "ut": UT,
            "fields": "f1,f2,f3,f4,f12,f13,f14"
        }
        res = requests.get(url, params=params, headers=headers, timeout=10)
        res.raise_for_status()
        data = res.json()
        print(f"--- 板块恐贪原始数据: {data} ---")
        
        # 数据结构: data.data 是 20 个板块的列表
        if data.get("data") and isinstance(data["data"], dict) and data["data"].get("data"):
            sectors = data["data"]["data"]
            # 字段 '3': 板块代码, '4': 板块名称, '5': 恐贪评分
            sectors_sorted = sorted(sectors, key=lambda x: float(x.get("5", 100)))[:5]
            for s in sectors_sorted:
                sentiment_data["sector_panic_top5"].append({
                    "name": s.get("4", ""),
                    "panic": s.get("5", 0)
                })
            has_data = True
    except Exception as e:
        print(f"[警告] 板块恐贪榜接口异常: {e}")

    # 4. 市场主线 (panicMThemeList, GBK)
    try:
        url = "https://push2delay.eastmoney.com/api/qt/stock/get"
        params = {
            "fn": "panicMThemeList",
            "ut": UT
        }
        res = requests.get(url, params=params, headers=headers, timeout=10)
        res.raise_for_status()
        data = json.loads(res.content.decode('gbk', errors='ignore'))
        print(f"--- 市场主线原始数据: {data} ---")
        
        # 字段 '5': 题材名称, '7': 强度 (>10000 才算主线)
        if data.get("data") and isinstance(data["data"], list):
            themes = []
            for t in data["data"]:
                if float(t.get("7", 0)) > 10000:
                    themes.append(t.get("5", ""))
            sentiment_data["market_theme"] = " / ".join(themes[:3])
            has_data = True
    except Exception as e:
        print(f"[警告] 市场主线接口异常: {e}")

    return sentiment_data if has_data else None

def main():
    data = fetch_market_sentiment()
    if data:
        os.makedirs("data", exist_ok=True)
        with open("data/sentiment.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"已保存情绪数据：恐贪={data['panic_index']}，主力净买={data['main_net_buy']} 亿")
    else:
        print("所有接口均未返回有效数据，跳过保存。")

if __name__ == "__main__":
    main()

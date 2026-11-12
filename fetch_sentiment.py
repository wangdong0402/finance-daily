import requests
import json
import os
from datetime import datetime

def fetch_market_sentiment():
    # 东财接口要求基本的浏览器伪装
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    sentiment_data = {
        "updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "panic_index": None,
        "suggested_position": None,
        "main_net_buy": 0.0,
        "sector_panic_top5": [],
        "market_theme": ""
    }

    # 1. 实时恐贪情绪 + 仓位建议 (GBK编码)
    try:
        panic_url = "https://push2.eastmoney.com/api/qt/panicindexst"
        res = requests.get(panic_url, headers=headers, timeout=10)
        res.raise_for_status()
        # 东财部分接口返回GBK，直接res.json()会报错，需要用content按GBK解码
        data = json.loads(res.content.decode('gbk', errors='ignore'))
        if data.get("data"):
            # 字段名可能随更新变化，优先尝试已知的键，找不到则遍历数据
            raw = data["data"]
            if isinstance(raw, dict):
                # 常见结构：{"panicIndex": 45.2, "suggestPosition": 45.2}
                sentiment_data["panic_index"] = raw.get("panicIndex") or raw.get("panic")
                sentiment_data["suggested_position"] = raw.get("suggestPosition") or raw.get("position")
            elif isinstance(raw, list) and len(raw) > 0:
                item = raw[0]
                sentiment_data["panic_index"] = item.get("panicIndex") or item.get("value")
                sentiment_data["suggested_position"] = item.get("suggestPosition")
    except Exception as e:
        print(f"[警告] 恐贪指数接口异常: {e}")

    # 2. 主力净买额 (UTF-8)
    try:
        netbuy_url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
        params = {
            "reportName": "RPT_MRRKET_FINNETBUYAMT1Y",
            "pageSize": 1,
            "pageNumber": 1,
            "sortTypes": -1,
            "sortColumns": "TRADE_DATE"
        }
        res = requests.get(netbuy_url, params=params, headers=headers, timeout=10)
        res.raise_for_status()
        data = res.json()
        if data.get("result") and data["result"].get("data"):
            item = data["result"]["data"][0]
            # 单位通常是元，转换为亿元
            raw_val = item.get("NET_BUY_AMT", 0)
            sentiment_data["main_net_buy"] = round(raw_val / 100000000, 2)
    except Exception as e:
        print(f"[警告] 主力净买额接口异常: {e}")

    # 3. 板块恐贪榜 Top5 (UTF-8)
    try:
        bk_url = "https://push2.eastmoney.com/api/qt/panicbklist"
        res = requests.get(bk_url, headers=headers, timeout=10)
        res.raise_for_status()
        data = res.json()
        if data.get("data"):
            sectors = data["data"]
            # 按恐贪值升序排序（越恐惧越靠前），取前5
            sectors_sorted = sorted(sectors, key=lambda x: x.get("panicValue", 100))[:5]
            for s in sectors_sorted:
                sentiment_data["sector_panic_top5"].append({
                    "name": s.get("bkName", ""),
                    "panic": s.get("panicValue", 0)
                })
    except Exception as e:
        print(f"[警告] 板块恐贪榜接口异常: {e}")

    # 4. 市场主线 (GBK)
    try:
        theme_url = "https://push2.eastmoney.com/api/qt/panicMThemeList"
        res = requests.get(theme_url, headers=headers, timeout=10)
        res.raise_for_status()
        data = json.loads(res.content.decode('gbk', errors='ignore'))
        if data.get("data"):
            themes = [t.get("themeName", "") for t in data["data"][:3]]
            sentiment_data["market_theme"] = " / ".join([t for t in themes if t])
    except Exception as e:
        print(f"[警告] 市场主线接口异常: {e}")

    # 如果四个数据全空，视为彻底失败
    if (sentiment_data["panic_index"] is None and 
        sentiment_data["main_net_buy"] == 0.0 and 
        not sentiment_data["sector_panic_top5"] and 
        not sentiment_data["market_theme"]):
        return None

    return sentiment_data

def main():
    data = fetch_market_sentiment()
    if data:
        os.makedirs("data", exist_ok=True)
        with open("data/sentiment.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"成功抓取情绪数据：恐贪 {data['panic_index']}，主力净买 {data['main_net_buy']} 亿")
    else:
        print("所有情绪数据接口均未返回有效内容，跳过保存。")

if __name__ == "__main__":
    main()

import requests
import json
import os
from datetime import datetime

def fetch_market_sentiment():
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

    try:
        # 1. 实时恐贪情绪 + 仓位建议
        panic_url = "https://emdc.eastmoney.com/api/qt/panicindexst"  # 示意端点
        panic_res = requests.get(panic_url, headers=headers, timeout=10).json()
        if panic_res.get("data"):
            sentiment_data["panic_index"] = panic_res["data"].get("panicIndex")
            sentiment_data["suggested_position"] = panic_res["data"].get("suggestPosition")

        # 2. 主力净买额
        netbuy_url = "https://datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPT_MRRKET_FINNETBUYAMT1Y"  # 示意端点
        netbuy_res = requests.get(netbuy_url, headers=headers, timeout=10).json()
        if netbuy_res.get("result") and netbuy_res["result"].get("data"):
            item = netbuy_res["result"]["data"][0]
            sentiment_data["main_net_buy"] = round(item.get("NET_BUY_AMT", 0) / 100000000, 2)

        # 3. 板块恐贪榜 Top5
        bk_url = "https://emdc.eastmoney.com/api/qt/panicbklist"  # 示意端点
        bk_res = requests.get(bk_url, headers=headers, timeout=10).json()
        if bk_res.get("data"):
            sectors = sorted(bk_res["data"], key=lambda x: x.get("panicValue", 0))
            for s in sectors[:5]:
                sentiment_data["sector_panic_top5"].append({
                    "name": s.get("bkName", ""),
                    "panic": s.get("panicValue", 0)
                })

        # 4. 市场主线
        theme_url = "https://emdc.eastmoney.com/api/qt/panicMThemeList"  # 示意端点
        theme_res = requests.get(theme_url, headers=headers, timeout=10).json()
        if theme_res.get("data"):
            themes = [t.get("themeName", "") for t in theme_res["data"][:3]]
            sentiment_data["market_theme"] = " / ".join(themes)

        return sentiment_data

    except Exception as e:
        print(f"获取市场情绪失败: {e}")
        return None

def main():
    data = fetch_market_sentiment()
    if data:
        os.makedirs("data", exist_ok=True)
        with open("data/sentiment.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"成功抓取情绪数据：恐贪 {data['panic_index']}，主力净买 {data['main_net_buy']} 亿")
    else:
        print("市场情绪数据抓取失败。")

if __name__ == "__main__":
    main()

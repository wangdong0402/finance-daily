import requests
import json
import os
from datetime import datetime

def fetch_market_sentiment():
    # 伪装请求头
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    sentiment_data = {
        "updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "indices": [],
        "breadth": {"up": 0, "down": 0, "flat": 0},
        "capital_flow": 0.0
    }

    try:
        # 1. 抓取三大指数（上证、深证、创业板）的实时行情和主力净流入
        # f12:代码, f14:名称, f2:最新价, f3:涨跌幅, f62:主力净流入
        idx_url = "https://push2.eastmoney.com/api/qt/ulist.np/get?fltt=2&secids=1.000001,0.399001,0.399006&fields=f12,f14,f2,f3,f62"
        idx_res = requests.get(idx_url, headers=headers, timeout=10).json()
        
        total_main_flow = 0
        if idx_res.get("data") and idx_res["data"].get("diff"):
            for item in idx_res["data"]["diff"]:
                flow = item.get("f62", 0)
                total_main_flow += flow
                sentiment_data["indices"].append({
                    "name": item.get("f14", ""),
                    "price": item.get("f2", 0),
                    "change": item.get("f3", 0)
                })
        # 主力净流入转换为“亿”为单位
        sentiment_data["capital_flow"] = round(total_main_flow / 100000000, 2)

        # 2. 抓取全市场涨跌家数 (f104:上涨, f105:下跌, f106:平盘)
        # 以上证指数（1.000001）的市场统计代表全市场概况
        breadth_url = "https://push2.eastmoney.com/api/qt/stock/get?secid=1.000001&fields=f104,f105,f106"
        breadth_res = requests.get(breadth_url, headers=headers, timeout=10).json()
        if breadth_res.get("data"):
            sentiment_data["breadth"] = {
                "up": breadth_res["data"].get("f104", 0),
                "down": breadth_res["data"].get("f105", 0),
                "flat": breadth_res["data"].get("f106", 0)
            }

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
        print(f"成功抓取市场情绪数据，主力净流入: {data['capital_flow']} 亿")
    else:
        print("市场情绪数据抓取失败，跳过保存。")

if __name__ == "__main__":
    main()

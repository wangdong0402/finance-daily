import requests
import json
import os
from datetime import datetime

def fetch_market_sentiment():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://data.eastmoney.com/"
    }
    UT = "bd1d9ddb04089700cf9c27f6f7426281"

    sentiment_data = {
        "updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "main_net_buy": 0.0,  # 新增：两市主力净买额
        "breadth": {"up": 0, "down": 0, "flat": 0},
        "sector_inflow_top10": [],
        "sector_outflow_top10": []
    }

    # 1. 两市主力净买额（使用之前验证成功的数据中心接口）
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
            raw_val = item.get("FIN_NETBUY_AMT", 0)
            sentiment_data["main_net_buy"] = round(raw_val / 100000000, 2)
        print("[信息] 主力净买额接口成功")
    except Exception as e:
        print(f"[警告] 主力净买额接口异常: {e}")

    # 2. 全市场涨跌家数
    try:
        url = "https://push2.eastmoney.com/api/qt/stock/get"
        params = {"secid": "1.000001", "fields": "f104,f105,f106", "ut": UT}
        res = requests.get(url, params=params, headers=headers, timeout=10)
        res.raise_for_status()
        data = res.json()
        if data.get("data"):
            sentiment_data["breadth"] = {
                "up": data["data"].get("f104", 0),
                "down": data["data"].get("f105", 0),
                "flat": data["data"].get("f106", 0)
            }
        print("[信息] 涨跌家数接口成功")
    except Exception as e:
        print(f"[警告] 涨跌家数接口异常: {e}")

    # 3. 行业板块资金流向（流入/流出 TOP10）
    try:
        url = "https://push2.eastmoney.com/api/qt/clist/get"
        base_params = {
            "pn": 1, "pz": 500, "np": 1, "fltt": 2, "invt": 2,
            "fs": "m:90+t:2", "fields": "f12,f14,f3,f62", "ut": UT, "fid": "f62"
        }

        # 主力净流入 TOP10
        params_in = {**base_params, "po": 1}
        res_in = requests.get(url, params=params_in, headers=headers, timeout=10).json()
        if res_in.get("data") and res_in["data"].get("diff"):
            for item in res_in["data"]["diff"][:10]:
                sentiment_data["sector_inflow_top10"].append({
                    "name": item.get("f14", ""),
                    "code": item.get("f12", ""),
                    "change": item.get("f3", 0),
                    "main_net": round(item.get("f62", 0) / 100000000, 2)
                })

        # 主力净流出 TOP10
        params_out = {**base_params, "po": 0}
        res_out = requests.get(url, params=params_out, headers=headers, timeout=10).json()
        if res_out.get("data") and res_out["data"].get("diff"):
            for item in res_out["data"]["diff"][:10]:
                sentiment_data["sector_outflow_top10"].append({
                    "name": item.get("f14", ""),
                    "code": item.get("f12", ""),
                    "change": item.get("f3", 0),
                    "main_net": round(item.get("f62", 0) / 100000000, 2)
                })
        print("[信息] 行业资金流接口成功")
    except Exception as e:
        print(f"[警告] 行业资金流接口异常: {e}")

    return sentiment_data

def main():
    data = fetch_market_sentiment()
    os.makedirs("data", exist_ok=True)
    with open("data/sentiment.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"情绪数据保存完成：主力净买={data['main_net_buy']} 亿，上涨 {data['breadth']['up']} 家。")

if __name__ == "__main__":
    main()

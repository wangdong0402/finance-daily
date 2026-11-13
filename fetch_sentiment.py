import requests
import json
import os
from datetime import datetime

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://data.eastmoney.com/"
}

def fetch_datacenter_flow(period):
    """
    通过数据中心接口获取行业资金流
    period: "5" 代表5日, "10" 代表10日
    """
    url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
    
    # 报表名称：行业资金流
    # 排序规则：按主力净流入（MAIN_NET_INFLOW）降序，取前10
    # 【修复语法错误】：f-string 中使用了单引号
    filter_str = f'(PERIOD="{period}")'
    
    params_in = {
        "reportName": "RPT_SECTOR_FUND_FLOW",
        "columns": "ALL",
        "pageSize": 10,
        "pageNumber": 1,
        "sortTypes": -1,
        "sortColumns": "MAIN_NET_INFLOW",
        "filter": filter_str
    }
    
    # 按主力净流入升序，取前10（即流出榜）
    params_out = params_in.copy()
    params_out["sortTypes"] = 1

    def get_data(params):
        try:
            res = requests.get(url, params=params, headers=HEADERS, timeout=10)
            res.raise_for_status()
            data = res.json()
            items = []
            if data.get("result") and data["result"].get("data"):
                for item in data["result"]["data"]:
                    # 数据中心返回的数值单位通常是元
                    net = round((item.get("MAIN_NET_INFLOW") or 0) / 100000000, 2)
                    items.append({
                        "name": item.get("SECTOR_NAME", ""),
                        "change": round(item.get("CHANGE_RATE") or 0, 2),
                        "main_net": net
                    })
            return items
        except Exception as e:
            print(f"[警告] 数据接口异常: {e}")
            return []

    print(f"[信息] 正在从数据中心抓取 {period} 日行业资金流...")
    inflow = get_data(params_in)
    outflow = get_data(params_out)
    return inflow, outflow

def main():
    sentiment_data = {
        "updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "periods": {}
    }

    # 抓取 10日 排行
    in_10, out_10 = fetch_datacenter_flow("10")
    sentiment_data["periods"]["10d"] = {"inflow": in_10, "outflow": out_10}

    # 抓取 5日 排行
    in_5, out_5 = fetch_datacenter_flow("5")
    sentiment_data["periods"]["5d"] = {"inflow": in_5, "outflow": out_5}

    os.makedirs("data", exist_ok=True)
    with open("data/sentiment.json", "w", encoding="utf-8") as f:
        json.dump(sentiment_data, f, ensure_ascii=False, indent=2)
    
    print(f"数据保存完成：10日流入第一名 {in_10[0]['name'] if in_10 else '无'}")

if __name__ == "__main__":
    main()

import requests
import json
import os
from datetime import datetime, timedelta

def fetch_eastmoney_reports():
    # 东方财富研报API
    url = "https://reportapi.eastmoney.com/report/list"
    
    # 动态获取最近3天的日期
    end_time = datetime.now().strftime("%Y-%m-%d")
    begin_time = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")

    params = {
        "pageSize": 200,     # 【核心修改】：把抓取数量从 20 扩大到 200
        "pageNo": 1,
        "beginTime": begin_time,
        "endTime": end_time,
        "qType": "0",        # 0代表个股研报
    }
    
    # 伪装成正常浏览器
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://data.eastmoney.com/"
    }

    try:
        response = requests.get(url, params=params, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
        reports = []
        
        if "data" in data and data["data"]:
            for item in data["data"]:
                info_code = item.get("infoCode", "")
                
                # 强制使用 PC 端单篇研报详情页链接
                link = f"https://data.eastmoney.com/report/info/{info_code}.html"
                
                reports.append({
                    "title": item.get("title", ""),
                    "org": item.get("orgSName", ""),
                    "date": item.get("publishDate", "")[:10],
                    "link": link,
                    "rating": item.get("emRatingName", ""),
                    "stock": item.get("stockName", ""),
                    "code": item.get("stockCode", "")
                })
        return reports
    except Exception as e:
        print(f"获取研报失败: {e}")
        return []

def main():
    reports = fetch_eastmoney_reports()
    os.makedirs("data", exist_ok=True)
    
    with open("data/reports.json", "w", encoding="utf-8") as f:
        json.dump(reports, f, ensure_ascii=False, indent=2)
        
    print(f"成功抓取 {len(reports)} 条研报并保存至 data/reports.json")

if __name__ == "__main__":
    main()

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
        "pageSize": 20,      # 抓取最新20条
        "pageNo": 1,
        "beginTime": begin_time,
        "endTime": end_time,
        "qType": "0",        # 0代表个股研报，1代表行业研报（这里我们抓个股）
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
                # 拼接研报详情页的链接
                info_code = item.get("infoCode", "")
                link = f"https://data.eastmoney.com/report/info/{info_code}.html"
                
                reports.append({
                    "title": item.get("title", ""),
                    "org": item.get("orgSName", ""),
                    "date": item.get("publishDate", "")[:10],
                    "link": link,
                    "rating": item.get("emRatingName", ""),  # 评级（如：买入、增持）
                    "stock": item.get("stockName", ""),      # 股票名称
                    "code": item.get("stockCode", "")        # 股票代码
                })
        return reports
    except Exception as e:
        print(f"获取研报失败: {e}")
        return []

def main():
    reports = fetch_eastmoney_reports()
    os.makedirs("data", exist_ok=True)
    
    # 保存为独立的 JSON 文件，不影响原来的新闻数据
    with open("data/reports.json", "w", encoding="utf-8") as f:
        json.dump(reports, f, ensure_ascii=False, indent=2)
        
    print(f"成功抓取 {len(reports)} 条研报并保存至 data/reports.json")

if __name__ == "__main__":
    main()

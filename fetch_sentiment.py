import akshare as ak
import json
import os
import time
from datetime import datetime

def fetch_ths_sector_flow(symbol):
    """获取同花顺行业资金流排行"""
    try:
        # 【核心修复】：将接口名更改为 stock_fund_flow_industry_ths
        df = ak.stock_fund_flow_industry_ths(symbol=symbol)
        
        # 兼容新版接口的排序（如果存在"净额"列）
        if "净额" in df.columns:
            df = df.sort_values(by="净额", ascending=False)
        
        inflow = []
        for _, row in df.head(10).iterrows():
            inflow.append({
                "name": str(row.get("行业", "")),
                "change": round(float(row.get("行业-涨跌幅", 0) or 0), 2),
                "main_net": round(float(row.get("净额", 0) or 0), 2)
            })
        
        outflow = []
        for _, row in df.tail(10).iloc[::-1].iterrows():
            outflow.append({
                "name": str(row.get("行业", "")),
                "change": round(float(row.get("行业-涨跌幅", 0) or 0), 2),
                "main_net": round(float(row.get("净额", 0) or 0), 2)
            })
        print(f"[成功] {symbol}: 流入 {len(inflow)} 条，流出 {len(outflow)} 条")
        return inflow, outflow
    except Exception as e:
        print(f"[警告] {symbol} 接口异常: {e}")
        return [], []

def main():
    sentiment_data = {
        "updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "periods": {}
    }

    periods = [("20d", "20日排行"), ("10d", "10日排行"), ("5d", "5日排行")]
    for key, symbol in periods:
        in_data, out_data = fetch_ths_sector_flow(symbol)
        sentiment_data["periods"][key] = {"inflow": in_data, "outflow": out_data}
        time.sleep(1) # 防封延迟

    os.makedirs("data", exist_ok=True)
    with open("data/sentiment.json", "w", encoding="utf-8") as f:
        json.dump(sentiment_data, f, ensure_ascii=False, indent=2)
    print("情绪数据保存完成。")

if __name__ == "__main__":
    main()

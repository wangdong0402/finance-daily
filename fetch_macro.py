import akshare as ak
import json
import os
import pandas as pd
from datetime import datetime

def clean_data(df, date_col, value_col, target_len=13):
    """
    清洗数据：提取指定列，转为正序，取最近 target_len 期，并处理空值
    """
    try:
        # 兼容不同版本的列名
        col_date = [c for c in df.columns if date_col in c][0]
        col_val = [c for c in df.columns if value_col in c][0]
        
        df = df[[col_date, col_val]].copy()
        df.columns = ['date', 'value']
        
        # 转换数值，处理 "---" 或空值
        df['value'] = pd.to_numeric(df['value'], errors='coerce')
        df = df.dropna()
        
        # 截取最近的数据 (因为 AKShare 返回的默认是倒序，最新的在第一行)
        df = df.head(target_len)
        
        # 翻转为正序（时间从旧到新）
        df = df.iloc[::-1]
        
        return {
            "labels": df['date'].tolist(),
            "data": [round(float(v), 2) for v in df['value'].tolist()]
        }
    except Exception as e:
        print(f"数据清洗失败 ({value_col}): {e}")
        return {"labels": [], "data": []}

def main():
    macro_data = {
        "updated": datetime.now().strftime("%Y-%m-%d"),
        "charts": {}
    }

    # 1. CPI
    try:
        df_cpi = ak.macro_china_cpi()
        # AKShare 的 CPI 列名通常包含 "全国-同比增长"
        macro_data["charts"]["cpi"] = clean_data(df_cpi, "月份", "全国-同比增长")
        print("[成功] CPI 数据抓取完成")
    except Exception as e:
        print(f"[警告] CPI 抓取失败: {e}")

    # 2. PPI
    try:
        df_ppi = ak.macro_china_ppi()
        macro_data["charts"]["ppi"] = clean_data(df_ppi, "月份", "当月同比增长")
        print("[成功] PPI 数据抓取完成")
    except Exception as e:
        print(f"[警告] PPI 抓取失败: {e}")

    # 3. M2 & M1
    try:
        df_money = ak.macro_china_money_supply()
        # 兼容不同版本列名
        m2_col = [c for c in df_money.columns if "M2" in c and "同比" in c]
        m1_col = [c for c in df_money.columns if "M1" in c and "同比" in c]
        
        if m2_col:
            macro_data["charts"]["m2"] = clean_data(df_money, "月份", m2_col[0])
        if m1_col:
            macro_data["charts"]["m1"] = clean_data(df_money, "月份", m1_col[0])
        print("[成功] 货币供应量 (M1/M2) 数据抓取完成")
    except Exception as e:
        print(f"[警告] 货币供应量抓取失败: {e}")

    # 4. 固定资产投资 (通常取当月同比增长)
    try:
        df_inv = ak.macro_china_gdzctz()
        # 兼容不同版本列名
        inv_col = [c for c in df_inv.columns if "同比" in c]
        if inv_col:
            macro_data["charts"]["invest"] = clean_data(df_inv, "月份", inv_col[0])
        print("[成功] 固定资产投资数据抓取完成")
    except Exception as e:
        print(f"[警告] 固定资产投资抓取失败: {e}")

    os.makedirs("data", exist_ok=True)
    with open("data/macro.json", "w", encoding="utf-8") as f:
        json.dump(macro_data, f, ensure_ascii=False, indent=2)
    
    print("宏观数据保存完成。")

if __name__ == "__main__":
    main()

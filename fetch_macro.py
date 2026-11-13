import akshare as ak
import json
import os
import pandas as pd
from datetime import datetime

# ================= 核心配置区 =================
# 以后想加新指标，只需要在这里加字典即可
MACRO_CONFIGS = [
    # 1. 货币与信用
    {
        "id": "shrzgm", "name": "社会融资规模增量 (亿元)", "category": "货币",
        "api": "macro_china_shrzgm", "x_col": "月份", "y_col": "社会融资规模增量",
        "type": "bar", "color": "#3b82f6"
    },
    # 2. 物价与通胀
    {
        "id": "cpi", "name": "居民消费价格指数 (CPI) - 同比 (%)", "category": "物价",
        "api": "macro_china_cpi", "x_col": "月份", "y_col": "全国-同比增长",
        "type": "line", "color": "#ef4444"
    },
    {
        "id": "ppi", "name": "工业生产者出厂价格 (PPI) - 同比 (%)", "category": "物价",
        "api": "macro_china_ppi", "x_col": "月份", "y_col": "当月同比增长",
        "type": "line", "color": "#8b5cf6"
    },
    # 3. 工业与景气 (PMI比较特殊，一个接口返回两个数据，后面单独处理)
    {
        "id": "gyzjz", "name": "工业增加值 - 同比 (%)", "category": "工业",
        "api": "macro_china_gyzjz", "x_col": "月份", "y_col": "同比增长",
        "type": "bar", "color": "#10b981"
    },
    # 4. 投资与外贸
    {
        "id": "trade", "name": "贸易帐差额 (亿美元)", "category": "外贸",
        "api": "macro_china_trade_balance", "x_col": "月份", "y_col": "当月差额",
        "type": "bar", "color": "#f59e0b"
    }
]

def extract_series(df, x_col_fuzzy, y_col_fuzzy, target_len=13):
    """模糊匹配列名并提取最近N期数据"""
    try:
        col_x = [c for c in df.columns if x_col_fuzzy in c][0]
        col_y = [c for c in df.columns if y_col_fuzzy in c][0]
        
        df = df[[col_x, col_y]].copy()
        df.columns = ['date', 'value']
        
        # 清除 "---" 等非数值
        df['value'] = pd.to_numeric(df['value'], errors='coerce')
        df = df.dropna()
        
        df = df.head(target_len).iloc[::-1] # 取近13期并正序
        
        return {
            "labels": df['date'].tolist(),
            "data": [round(float(v), 2) for v in df['value'].tolist()]
        }
    except Exception as e:
        print(f"  [警告] 数据解析失败 ({y_col_fuzzy}): {e}")
        return None

def main():
    macro_data = {
        "updated": datetime.now().strftime("%Y-%m-%d"),
        "charts": {}
    }

    # 批量抓取配置中的基础指标
    for cfg in MACRO_CONFIGS:
        print(f"[信息] 抓取 {cfg['name']} ...")
        try:
            func = getattr(ak, cfg["api"])
            df = func()
            result = extract_series(df, cfg["x_col"], cfg["y_col"])
            if result:
                macro_data["charts"][cfg["id"]] = {
                    "name": cfg["name"], "category": cfg["category"],
                    "type": cfg["type"], "color": cfg["color"],
                    **result
                }
        except Exception as e:
            print(f"  [失败] {cfg['name']}: {e}")

    # 特殊处理：PMI (包含制造业和非制造业)
    print("[信息] 抓取 PMI ...")
    try:
        df_pmi = ak.macro_china_pmi()
        mfg = extract_series(df_pmi, "月份", "制造业-指数")
        non_mfg = extract_series(df_pmi, "月份", "非制造业-指数")
        if mfg and non_mfg:
            macro_data["charts"]["pmi"] = {
                "name": "采购经理人指数 (PMI)", "category": "工业",
                "type": "multi_line", # 多线图
                "labels": mfg["labels"],
                "series": [
                    {"name": "制造业", "color": "#3b82f6", "data": mfg["data"]},
                    {"name": "非制造业", "color": "#f59e0b", "data": non_mfg["data"]}
                ],
                "baseline": 50  # 50 枯荣线
            }
    except Exception as e:
        print(f"  [失败] PMI: {e}")

    os.makedirs("data", exist_ok=True)
    with open("data/macro.json", "w", encoding="utf-8") as f:
        json.dump(macro_data, f, ensure_ascii=False, indent=2)
    print("宏观数据保存完成。")

if __name__ == "__main__":
    main()

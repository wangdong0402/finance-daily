import akshare as ak
import json
import os
import pandas as pd
import re
from datetime import datetime

# ================= 大满贯配置区 =================
MACRO_CONFIGS = [
    # 💵 货币与信用
    {"id": "shrzgm", "name": "社会融资规模增量 (亿元)", "category": "货币", "api": "macro_china_shrzgm", "x_col": "月份", "y_col": "社会融资规模增量", "type": "bar", "color": "#3b82f6"},
    {"id": "rmb_loan", "name": "新增人民币贷款 (亿元)", "category": "货币", "api": "macro_rmb_loan", "x_col": "月份", "y_col": "新增人民币贷款-总额", "type": "bar", "color": "#8b5cf6"},
    {"id": "lpr", "name": "贷款市场报价利率 LPR (%)", "category": "货币", "api": "macro_china_lpr", "x_col": "TRADE_DATE", "y_col": "LPR1Y", "type": "line", "color": "#f59e0b"}, # 这里的列名可能需要兼容
    
    # 📈 物价与通胀
    {"id": "cpi", "name": "居民消费价格指数 (CPI) - 同比 (%)", "category": "物价", "api": "macro_china_cpi", "x_col": "月份", "y_col": "全国-同比增长", "type": "line", "color": "#ef4444"},
    {"id": "ppi", "name": "工业生产者出厂价格 (PPI) - 同比 (%)", "category": "物价", "api": "macro_china_ppi", "x_col": "月份", "y_col": "当月同比增长", "type": "line", "color": "#10b981"},
    {"id": "qyspjg", "name": "企业商品价格指数 - 同比 (%)", "category": "物价", "api": "macro_china_qyspjg", "x_col": "月份", "y_col": "同比增长", "type": "line", "color": "#ec4899"},

    # 🏭 工业与景气
    {"id": "gyzjz", "name": "工业增加值 - 同比 (%)", "category": "工业", "api": "macro_china_gyzjz", "x_col": "月份", "y_col": "同比增长", "type": "bar", "color": "#14b8a6"},

    # 🏗️ 投资与外贸
    {"id": "gdzctz", "name": "固定资产投资 - 同比 (%)", "category": "外贸", "api": "macro_china_gdzctz", "x_col": "月份", "y_col": "同比增长", "type": "line", "color": "#6366f1"},
    {"id": "trade", "name": "贸易帐差额 (亿美元)", "category": "外贸", "api": "macro_china_trade_balance", "x_col": "月份", "y_col": "当月差额", "type": "bar", "color": "#f97316"},
    {"id": "fdi", "name": "外商直接投资 (FDI) - 同比 (%)", "category": "外贸", "api": "macro_china_fdi", "x_col": "月份", "y_col": "同比增长", "type": "line", "color": "#64748b"}
]

def extract_series(df, x_col_fuzzy, y_col_fuzzy, target_len=13):
    """模糊匹配列名，强制统一按时间排序"""
    try:
        col_x = [c for c in df.columns if x_col_fuzzy in c][0]
        col_y = [c for c in df.columns if y_col_fuzzy in c][0]
        
        df = df[[col_x, col_y]].copy()
        df.columns = ['date', 'value']
        
        df['value'] = pd.to_numeric(df['value'], errors='coerce')
        df = df.dropna()
        
        def parse_date_to_sortable(d):
            d_str = str(d)
            # 匹配 4 位数字年份，后跟任意字符，再跟 1-2 位数字月份
            match = re.search(r'(\d{4})\D*(\d{1,2})', d_str)
            if match:
                y, m = match.groups()
                return f"{y}-{int(m):02d}"
            return d_str
            
        df['sort_date'] = df['date'].apply(parse_date_to_sortable)
        df = df.sort_values(by='sort_date').reset_index(drop=True)
        df = df.tail(target_len)
        
        return {
            "labels": df['date'].tolist(),
            "data": [round(float(v), 2) for v in df['value'].tolist()]
        }
    except Exception as e:
        print(f"  [警告] 解析失败 ({y_col_fuzzy}): {e}")
        return None

def main():
    macro_data = {
        "updated": datetime.now().strftime("%Y-%m-%d"),
        "charts": {}
    }

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

    # 特殊处理 1：PMI (多线图)
    try:
        df_pmi = ak.macro_china_pmi()
        mfg = extract_series(df_pmi, "月份", "制造业-指数")
        non_mfg = extract_series(df_pmi, "月份", "非制造业-指数")
        if mfg and non_mfg:
            macro_data["charts"]["pmi"] = {
                "name": "采购经理人指数 (PMI)", "category": "工业", "type": "multi_line",
                "labels": mfg["labels"],
                "series": [
                    {"name": "制造业", "color": "#3b82f6", "data": mfg["data"]},
                    {"name": "非制造业", "color": "#f59e0b", "data": non_mfg["data"]}
                ],
                "baseline": 50
            }
    except Exception as e:
        print(f"  [失败] PMI: {e}")

    # 特殊处理 2：货币供应量 M0/M1/M2 (多线图)
    try:
        df_money = ak.macro_china_money_supply()
        m0 = extract_series(df_money, "月份", "M0-同比")
        m1 = extract_series(df_money, "月份", "M1-同比")
        m2 = extract_series(df_money, "月份", "M2-同比")
        if m0 and m1 and m2:
            macro_data["charts"]["money_supply"] = {
                "name": "货币供应量同比增速 (%)", "category": "货币", "type": "multi_line",
                "labels": m0["labels"],
                "series": [
                    {"name": "M0", "color": "#ef4444", "data": m0["data"]},
                    {"name": "M1", "color": "#10b981", "data": m1["data"]},
                    {"name": "M2", "color": "#3b82f6", "data": m2["data"]}
                ]
            }
    except Exception as e:
        print(f"  [失败] 货币供应量: {e}")

    os.makedirs("data", exist_ok=True)
    with open("data/macro.json", "w", encoding="utf-8") as f:
        json.dump(macro_data, f, ensure_ascii=False, indent=2)
    print("宏观全量数据保存完成。")

if __name__ == "__main__":
    main()

import akshare as ak
import json
import os
import pandas as pd
import re
from datetime import datetime

# ================= 调整了顺序的配置区 =================
MACRO_CONFIGS = [
    # 💵 货币与信用 (贷款提至社融前)
    {"id": "rmb_loan", "name": "新增人民币贷款 (亿元)", "category": "货币", "api": "macro_rmb_loan", "x_col": "月份", "y_col": "总额", "type": "bar", "color": "#8b5cf6"},
    {"id": "shrzgm", "name": "社会融资规模增量 (亿元)", "category": "货币", "api": "macro_china_shrzgm", "x_col": "月份", "y_col": "社会融资规模增量", "type": "bar", "color": "#3b82f6"},
    {"id": "lpr", "name": "贷款市场报价利率 LPR (%)", "category": "货币", "api": "macro_china_lpr", "x_col": "TRADE_DATE", "y_col": "LPR1Y", "type": "line", "color": "#f59e0b"},
    
    # 📈 物价与通胀
    {"id": "cpi", "name": "居民消费价格指数 (CPI) - 同比 (%)", "category": "物价", "api": "macro_china_cpi", "x_col": "月份", "y_col": "全国-同比增长", "type": "line", "color": "#ef4444"},
    {"id": "ppi", "name": "工业生产者出厂价格 (PPI) - 同比 (%)", "category": "物价", "api": "macro_china_ppi", "x_col": "月份", "y_col": "当月同比增长", "type": "line", "color": "#10b981"},
    {"id": "qyspjg", "name": "企业商品价格指数 - 同比 (%)", "category": "物价", "api": "macro_china_qyspjg", "x_col": "月份", "y_col": "同比增长", "type": "line", "color": "#ec4899"},
    
    # 🏭 工业与景气
    {"id": "gyzjz", "name": "工业增加值 - 同比 (%)", "category": "工业", "api": "macro_china_gyzjz", "x_col": "月份", "y_col": "同比增长", "type": "bar", "color": "#14b8a6"},
    
    # 🏗️ 投资与外贸
    {"id": "gdzctz", "name": "固定资产投资 - 同比 (%)", "category": "外贸", "api": "macro_china_gdzctz", "x_col": "月份", "y_col": "同比增长", "type": "line", "color": "#6366f1"},
    {"id": "trade", "name": "贸易帐差额 (亿美元)", "category": "外贸", "api": "macro_china_trade_balance", "x_col": "月份", "y_col": "差额", "type": "bar", "color": "#f97316"},
]

def extract_series(df, x_col_fuzzy, y_col_fuzzy, target_len=13):
    """模糊匹配列名并提取最近N期数据（防崩溃机制）"""
    try:
        col_x_candidates = [c for c in df.columns if x_col_fuzzy in c]
        col_y_candidates = [c for c in df.columns if y_col_fuzzy in c]
        
        if not col_x_candidates or not col_y_candidates:
            print(f"    [调试] 找不到目标列。尝试匹配 '{x_col_fuzzy}' 和 '{y_col_fuzzy}'")
            return None
            
        col_x = col_x_candidates[0]
        col_y = col_y_candidates[0]
        
        df = df[[col_x, col_y]].copy()
        df.columns = ['date', 'value']
        
        df['value'] = pd.to_numeric(df['value'], errors='coerce')
        df = df.dropna()
        
        def parse_date_to_sortable(d):
            d_str = str(d)
            match = re.search(r'(\d{4})\D*(\d{1,2})', d_str)
            if match:
                y, m = match.groups()
                return f"{y}-{int(m):02d}"
            return d_str
            
        df['sort_date'] = df['date'].apply(parse_date_to_sortable)
        df = df.sort_values(by='sort_date').reset_index(drop=True)
        df = df.tail(target_len)
        
        labels = [str(x)[:10] for x in df['date'].tolist()]
        
        return {
            "labels": labels,
            "data": [round(float(v), 2) for v in df['value'].tolist()]
        }
    except Exception as e:
        print(f"    [警告] 数据解析失败: {e}")
        return None

def main():
    macro_data = {
        "updated": datetime.now().strftime("%Y-%m-%d"),
        "charts": {}
    }

    # ================= 1. 最先抓取货币供应量 (确保排第一) =================
    print("[信息] 抓取 货币供应量 M0/M1/M2 ...")
    try:
        df_money = ak.macro_china_money_supply()
        col_date = [c for c in df_money.columns if "月份" in c][0]
        col_m0 = [c for c in df_money.columns if "M0" in c and "同比" in c][0]
        col_m1 = [c for c in df_money.columns if "M1" in c and "同比" in c][0]
        col_m2 = [c for c in df_money.columns if "M2" in c and "同比" in c][0]
        
        df_money['sort_date'] = df_money[col_date].apply(lambda x: str(x))
        df_money = df_money.sort_values(by='sort_date').tail(13)
        labels = [str(x)[:10] for x in df_money[col_date].tolist()]
        
        macro_data["charts"]["money_supply"] = {
            "name": "货币供应量同比增速 (%)", "category": "货币", "type": "multi_line",
            "labels": labels,
            "series": [
                {"name": "M0", "color": "#ef4444", "data": [round(float(v), 2) for v in df_money[col_m0].tolist()]},
                {"name": "M1", "color": "#10b981", "data": [round(float(v), 2) for v in df_money[col_m1].tolist()]},
                {"name": "M2", "color": "#3b82f6", "data": [round(float(v), 2) for v in df_money[col_m2].tolist()]}
            ]
        }
        print("[信息] 货币供应量抓取成功")
    except Exception as e:
        print(f"  [失败] 货币供应量异常: {e}")

    # ================= 2. 遍历抓取配置指标 (新增贷款、社融等) =================
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
            print(f"  [失败] {cfg['name']} 接口异常: {e}")

    # ================= 3. PMI =================
    print("[信息] 抓取 PMI ...")
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
        print(f"  [失败] PMI 接口异常: {e}")

    # ================= 4. 海关进出口 =================
    print("[信息] 抓取 海关进出口增减情况 ...")
    try:
        df_hgjck = ak.macro_china_hgjck()
        exp = extract_series(df_hgjck, "月份", "当月出口额-金额")
        imp = extract_series(df_hgjck, "月份", "当月进口额-金额")
        
        if exp and imp:
            macro_data["charts"]["trade_amount"] = {
                "name": "海关进出口当月金额 (亿美元)", "category": "外贸", "type": "multi_line",
                "labels": exp["labels"],
                "series": [
                    {"name": "出口额", "color": "#ef4444", "data": exp["data"]},
                    {"name": "进口额", "color": "#3b82f6", "data": imp["data"]}
                ]
            }
            print("[信息] 海关进出口数据抓取成功")
    except Exception as e:
        print(f"  [失败] 海关进出口数据异常: {e}")

    os.makedirs("data", exist_ok=True)
    with open("data/macro.json", "w", encoding="utf-8") as f:
        json.dump(macro_data, f, ensure_ascii=False, indent=2)
    print(f"宏观全量数据保存完成，共 {len(macro_data['charts'])} 个图表。")

if __name__ == "__main__":
    main()

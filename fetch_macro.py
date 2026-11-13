import akshare as ak
import json
import os
import pandas as pd
import re
from datetime import datetime

MACRO_CONFIGS = [
    # 💵 货币与信用
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
    try:
        col_x = [c for c in df.columns if x_col_fuzzy in c][0]
        col_y = [c for c in df.columns if y_col_fuzzy in c][0]
        df = df[[col_x, col_y]].copy()
        df.columns = ['date', 'value']
        df['value'] = pd.to_numeric(df['value'], errors='coerce')
        df = df.dropna()
        def parse_date_to_sortable(d):
            match = re.search(r'(\d{4})\D*(\d{1,2})', str(d))
            if match:
                return f"{match.group(1)}-{int(match.group(2)):02d}"
            return str(d)
        df['sort_date'] = df['date'].apply(parse_date_to_sortable)
        df = df.sort_values(by='sort_date').reset_index(drop=True).tail(target_len)
        return {"labels": [str(x)[:10] for x in df['date']], "data": [round(float(v), 2) for v in df['value']]}
    except Exception as e:
        print(f"    [警告] 数据解析失败: {e}")
        return None

def resample_monthly(df, date_col, value_cols):
    """强健的按月重采样逻辑"""
    try:
        df = df.copy()
        df['dt'] = pd.to_datetime(df[date_col], errors='coerce')
        df = df.dropna(subset=['dt'])
        
        for col in value_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
        df = df.set_index('dt')
        # 关键修复：使用最新的 'ME' 代替旧版的 'M'
        monthly = df[value_cols].resample('ME').last().dropna(how='all').tail(13)
        if monthly.empty:
            return None, []
        labels = [d.strftime('%Y-%m') for d in monthly.index]
        return monthly, labels
    except Exception as e:
        print(f"  [重采样报错] {e}")
        return None, []

def main():
    macro_data = {"updated": datetime.now().strftime("%Y-%m-%d"), "charts": {}}

    for cfg in MACRO_CONFIGS:
        print(f"[信息] 抓取 {cfg['name']} ...")
        try:
            df = getattr(ak, cfg["api"])()
            result = extract_series(df, cfg["x_col"], cfg["y_col"])
            if result:
                macro_data["charts"][cfg["id"]] = {"name": cfg["name"], "category": cfg["category"], "type": cfg["type"], "color": cfg["color"], **result}
        except Exception as e:
            print(f"  [失败] {cfg['name']}: {e}")

    # 特殊处理：PMI
    try:
        df_pmi = ak.macro_china_pmi()
        mfg = extract_series(df_pmi, "月份", "制造业-指数")
        non_mfg = extract_series(df_pmi, "月份", "非制造业-指数")
        if mfg and non_mfg:
            macro_data["charts"]["pmi"] = {"name": "采购经理人指数 (PMI)", "category": "工业", "type": "multi_line", "labels": mfg["labels"], "baseline": 50, "series": [{"name": "制造业", "color": "#3b82f6", "data": mfg["data"]}, {"name": "非制造业", "color": "#f59e0b", "data": non_mfg["data"]}]}
    except Exception as e: print(f"PMI失败: {e}")
    
    # 特殊处理：货币供应量
    try:
        df_money = ak.macro_china_money_supply()
        col_date = [c for c in df_money.columns if "月份" in c][0]
        cols = [[c for c in df_money.columns if f"M{i}" in c and "同比" in c][0] for i in range(3)]
        df_money['sort_date'] = df_money[col_date].apply(lambda x: str(x))
        df_money = df_money.sort_values(by='sort_date').tail(13)
        macro_data["charts"]["money_supply"] = {"name": "货币供应量同比增速 (%)", "category": "货币", "type": "multi_line", "labels": [str(x)[:10] for x in df_money[col_date]], "series": [{"name": f"M{i}", "color": ["#ef4444", "#10b981", "#3b82f6"][i], "data": [round(float(v), 2) for v in df_money[cols[i]]]} for i in range(3)]}
    except Exception as e: print(f"货币供应量失败: {e}")

    # 特殊处理：海关进出口
    try:
        df_hgjck = ak.macro_china_hgjck()
        exp = extract_series(df_hgjck, "月份", "当月出口额-金额")
        imp = extract_series(df_hgjck, "月份", "当月进口额-金额")
        if exp and imp:
            macro_data["charts"]["trade_amount"] = {"name": "海关进出口当月金额 (亿美元)", "category": "外贸", "type": "multi_line", "labels": exp["labels"], "series": [{"name": "出口额", "color": "#ef4444", "data": exp["data"]}, {"name": "进口额", "color": "#3b82f6", "data": imp["data"]}]}
    except Exception as e: print(f"海关进出口失败: {e}")

    # ================= 新增：大类资产 =================
    # 5. 国债收益率
    print("[信息] 抓取 10年期国债收益率 ...")
    try:
        df_bond = ak.bond_zh_us_rate()
        print(f"    [调试] 国债原始列名: {df_bond.columns.tolist()}")
        
        col_cn = next((c for c in df_bond.columns if "中国" in c and "10年" in c), None)
        col_us = next((c for c in df_bond.columns if "美国" in c and "10年" in c), None)
        
        if col_cn and col_us:
            monthly, labels = resample_monthly(df_bond, "日期", [col_cn, col_us])
            if monthly is not None:
                macro_data["charts"]["bond_yield"] = {
                    "name": "10年期国债收益率 (%)", "category": "大类资产", "type": "multi_line",
                    "labels": labels,
                    "series": [
                        {"name": "中国", "color": "#ef4444", "data": [round(float(v), 2) for v in monthly[col_cn]]},
                        {"name": "美国", "color": "#3b82f6", "data": [round(float(v), 2) for v in monthly[col_us]]}
                    ]
                }
        else:
            print(f"    [失败] 未找到匹配的国债列名")
    except Exception as e:
        print(f"  [失败] 国债收益率异常: {e}")

    # 6. 汇率
    print("[信息] 抓取 美元兑人民币汇率 ...")
    try:
        df_fx = ak.macro_china_rmb()
        print(f"    [调试] 汇率原始列名: {df_fx.columns.tolist()}")
        
        col_fx = next((c for c in df_fx.columns if "美元" in c and "中间价" in c), None)
        
        if col_fx:
            monthly, labels = resample_monthly(df_fx, "日期", [col_fx])
            if monthly is not None:
                macro_data["charts"]["exchange_rate"] = {
                    "name": "美元兑人民币中间价", "category": "大类资产", "type": "line", "color": "#10b981",
                    "labels": labels,
                    "data": [round(float(v), 4) for v in monthly[col_fx]]
                }
        else:
            print(f"    [失败] 未找到匹配的汇率列名")
    except Exception as e:
        print(f"  [失败] 汇率异常: {e}")

    os.makedirs("data", exist_ok=True)
    with open("data/macro.json", "w", encoding="utf-8") as f:
        json.dump(macro_data, f, ensure_ascii=False, indent=2)
    print(f"宏观全量数据保存完成，共 {len(macro_data['charts'])} 个图表。")

if __name__ == "__main__":
    main()

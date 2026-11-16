import akshare as ak
import json
import os
import pandas as pd
import re
import time
from datetime import datetime

# 宏观指标配置
MACRO_CONFIGS = [
    # 💵 货币与信用
    {"id": "rmb_loan", "name": "新增人民币贷款 (亿元)", "category": "货币", "api": "macro_china_rmb_loan_ths", "x_col": "月份", "y_col": "总额", "type": "bar", "color": "#8b5cf6"},
    {"id": "shrzgm", "name": "社会融资规模增量 (亿元)", "category": "货币", "api": "macro_china_social_financing", "x_col": "月份", "y_col": "社会融资规模增量", "type": "bar", "color": "#3b82f6"},
    # 【核心修复】：将 x_col 改为 "日期" 以防接口返回中文列名
    {"id": "lpr", "name": "贷款市场报价利率 LPR (%)", "category": "货币", "api": "interest_rate_lpr_em", "x_col": "日期", "y_col": "LPR1Y", "type": "line", "color": "#f59e0b"},
    
    # 📈 物价与通胀
    {"id": "cpi", "name": "居民消费价格指数 (CPI) - 同比 (%)", "category": "物价", "api": "macro_china_cpi", "x_col": "月份", "y_col": "全国-同比增长", "type": "line", "color": "#ef4444"},
    {"id": "ppi", "name": "工业生产者出厂价格 (PPI) - 同比 (%)", "category": "物价", "api": "macro_china_ppi", "x_col": "月份", "y_col": "当月同比增长", "type": "line", "color": "#10b981"},
    {"id": "qyspjg", "name": "企业商品价格指数 - 同比 (%)", "category": "物价", "api": "macro_china_cgpi", "x_col": "月份", "y_col": "同比增长", "type": "line", "color": "#ec4899"},
    
    # 🏭 工业与景气
    {"id": "gyzjz", "name": "工业增加值 - 同比 (%)", "category": "工业", "api": "macro_china_industrial_value_added", "x_col": "月份", "y_col": "同比增长", "type": "bar", "color": "#14b8a6"},
    
    # 🏗️ 投资与外贸
    {"id": "gdzctz", "name": "固定资产投资 - 同比 (%)", "category": "外贸", "api": "macro_china_fixed_asset_investment", "x_col": "月份", "y_col": "同比增长", "type": "line", "color": "#6366f1"},
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

def resample_monthly(df, date_col, value_cols, target_len=13):
    try:
        df = df.copy()
        df['dt'] = pd.to_datetime(df[date_col], errors='coerce')
        df = df.dropna(subset=['dt'])
        for col in value_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df = df.set_index('dt').sort_index()
        monthly = df[value_cols].resample('ME').last().dropna(how='all').tail(target_len)
        if monthly.empty:
            return None, []
        labels = [d.strftime('%Y-%m') for d in monthly.index]
        return monthly, labels
    except Exception as e:
        print(f"  [重采样报错] {e}")
        return None, []

def main():
    old_charts = {}
    if os.path.exists("data/macro.json"):
        try:
            with open("data/macro.json", "r", encoding="utf-8") as f:
                old_charts = json.load(f).get("charts", {})
                print(f"[信息] 已加载历史宏观数据，共 {len(old_charts)} 个图表")
        except Exception as e:
            print(f"[警告] 读取旧宏观数据失败: {e}")

    macro_data = {"updated": datetime.now().strftime("%Y-%m-%d"), "charts": {}}
    new_charts = macro_data["charts"]

    # 1. 货币供应量
    print("[信息] 抓取 货币供应量 M0/M1/M2 ...")
    try:
        df_money = ak.macro_china_money_supply_em()
        col_date = [c for c in df_money.columns if "月份" in c][0]
        cols = [[c for c in df_money.columns if f"M{i}" in c and "同比" in c][0] for i in range(3)]
        df_money['sort_date'] = df_money[col_date].apply(lambda x: str(x))
        df_money = df_money.sort_values(by='sort_date').tail(13)
        new_charts["money_supply"] = {"name": "货币供应量同比增速 (%)", "category": "货币", "type": "multi_line", "labels": [str(x)[:10] for x in df_money[col_date]], "series": [{"name": f"M{i}", "color": ["#ef4444", "#10b981", "#3b82f6"][i], "data": [round(float(v), 2) for v in df_money[cols[i]]]} for i in range(3)]}
    except Exception as e:
        print(f"  [失败] 货币供应量异常: {e}")
        if "money_supply" in old_charts: 
            new_charts["money_supply"] = old_charts["money_supply"]
            print("    [兜底] 已恢复历史货币供应量数据")
    time.sleep(1)

    # 2. 遍历基础配置
    for cfg in MACRO_CONFIGS:
        print(f"[信息] 抓取 {cfg['name']} ...")
        try:
            df = getattr(ak, cfg["api"])()
            result = extract_series(df, cfg["x_col"], cfg["y_col"])
            if result:
                new_charts[cfg["id"]] = {"name": cfg["name"], "category": cfg["category"], "type": cfg["type"], "color": cfg["color"], **result}
            else:
                raise ValueError("数据解析为空")
        except Exception as e:
            print(f"  [失败] {cfg['name']}: {e}")
            if cfg["id"] in old_charts:
                new_charts[cfg["id"]] = old_charts[cfg["id"]]
                print(f"    [兜底] 已恢复历史 {cfg['name']} 数据")
        time.sleep(1)

    # 3. PMI
    print("[信息] 抓取 PMI ...")
    try:
        df_pmi = ak.macro_china_pmi()
        mfg = extract_series(df_pmi, "月份", "制造业-指数")
        non_mfg = extract_series(df_pmi, "月份", "非制造业-指数")
        if mfg and non_mfg:
            new_charts["pmi"] = {"name": "采购经理人指数 (PMI)", "category": "工业", "type": "multi_line", "labels": mfg["labels"], "baseline": 50, "series": [{"name": "制造业", "color": "#3b82f6", "data": mfg["data"]}, {"name": "非制造业", "color": "#f59e0b", "data": non_mfg["data"]}]}
        else:
            raise ValueError("数据解析为空")
    except Exception as e: 
        print(f"PMI失败: {e}")
        if "pmi" in old_charts:
            new_charts["pmi"] = old_charts["pmi"]
            print("    [兜底] 已恢复历史 PMI 数据")
    time.sleep(1)
    
    # 4. 海关进出口
    print("[信息] 抓取 海关进出口增减情况 ...")
    try:
        df_hgjck = ak.macro_china_customs_trade()
        exp = extract_series(df_hgjck, "月份", "当月出口额-金额")
        imp = extract_series(df_hgjck, "月份", "当月进口额-金额")
        if exp and imp:
            new_charts["trade_amount"] = {"name": "海关进出口当月金额 (亿美元)", "category": "外贸", "type": "multi_line", "labels": exp["labels"], "series": [{"name": "出口额", "color": "#ef4444", "data": exp["data"]}, {"name": "进口额", "color": "#3b82f6", "data": imp["data"]}]}
        else:
            raise ValueError("数据解析为空")
    except Exception as e: 
        print(f"海关进出口失败: {e}")
        if "trade_amount" in old_charts:
            new_charts["trade_amount"] = old_charts["trade_amount"]
            print("    [兜底] 已恢复历史 海关进出口 数据")
    time.sleep(1)

    # 5. 国债收益率
    print("[信息] 抓取 10年期国债收益率 ...")
    try:
        df_bond = ak.bond_zh_us_yield_em()
        col_cn = next((c for c in df_bond.columns if "中国" in c and "10年" in c), None)
        col_us = next((c for c in df_bond.columns if "美国" in c and "10年" in c), None)
        if col_cn and col_us:
            monthly, labels = resample_monthly(df_bond, "日期", [col_cn, col_us])
            if monthly is not None:
                new_charts["bond_yield"] = {"name": "10年期国债收益率 (%)", "category": "大类资产", "type": "multi_line", "labels": labels, "series": [{"name": "中国", "color": "#ef4444", "data": [round(float(v), 2) for v in monthly[col_cn]]}, {"name": "美国", "color": "#3b82f6", "data": [round(float(v), 2) for v in monthly[col_us]]}]}
            else:
                raise ValueError("数据解析为空")
    except Exception as e: 
        print(f"国债异常: {e}")
        if "bond_yield" in old_charts:
            new_charts["bond_yield"] = old_charts["bond_yield"]
            print("    [兜底] 已恢复历史 国债收益率 数据")
    time.sleep(1)

    # 6. 汇率
    print("[信息] 抓取 美元兑人民币汇率 ...")
    try:
        df_fx = ak.fx_central_parity_safe()
        col_date = next((c for c in df_fx.columns if "日期" in c), None)
        col_val = next((c for c in df_fx.columns if "美元" in c), None)
        if col_date and col_val:
            df_fx[col_val] = pd.to_numeric(df_fx[col_val], errors='coerce') / 100.0
            monthly, labels = resample_monthly(df_fx, col_date, [col_val])
            if monthly is not None:
                new_charts["exchange_rate"] = {"name": "美元兑人民币中间价", "category": "大类资产", "type": "line", "color": "#10b981", "labels": labels, "data": [round(float(v), 4) for v in monthly[col_val]]}
            else:
                raise ValueError("数据解析为空")
    except Exception as e: 
        print(f"汇率异常: {e}")
        if "exchange_rate" in old_charts:
            new_charts["exchange_rate"] = old_charts["exchange_rate"]
            print("    [兜底] 已恢复历史 汇率 数据")
    time.sleep(1)

    # 7. 沪深300 PE
    print("[信息] 抓取 沪深300 PE ...")
    try:
        df_pe = ak.stock_index_pe_lg(symbol="沪深300")
        col_date = next((c for c in df_pe.columns if "日期" in c), None)
        col_val = next((c for c in df_pe.columns if "滚动市盈率" in c or "等权静态市盈率" in c or "市盈率" in c), None)
        if col_date and col_val:
            monthly, labels = resample_monthly(df_pe, col_date, [col_val], target_len=36)
            if monthly is not None:
                new_charts["hs300_pe"] = {"name": "沪深300 滚动市盈率 (PE-TTM，近三年)", "category": "大类资产", "type": "line", "color": "#8b5cf6", "labels": labels, "data": [round(float(v), 2) for v in monthly[col_val]]}
            else:
                raise ValueError("数据解析为空")
    except Exception as e: 
        print(f"沪深300 PE异常: {e}")
        if "hs300_pe" in old_charts:
            new_charts["hs300_pe"] = old_charts["hs300_pe"]
            print("    [兜底] 已恢复历史 沪深300 PE 数据")
    time.sleep(1)

    # 8. 中证500 PE
    print("[信息] 抓取 中证500 PE ...")
    try:
        df_pe500 = ak.stock_index_pe_lg(symbol="中证500")
        col_date = next((c for c in df_pe500.columns if "日期" in c), None)
        col_val = next((c for c in df_pe500.columns if "滚动市盈率" in c or "等权静态市盈率" in c or "市盈率" in c), None)
        if col_date and col_val:
            monthly, labels = resample_monthly(df_pe500, col_date, [col_val], target_len=36)
            if monthly is not None:
                new_charts["zz500_pe"] = {"name": "中证500 滚动市盈率 (PE-TTM，近三年)", "category": "大类资产", "type": "line", "color": "#ec4899", "labels": labels, "data": [round(float(v), 2) for v in monthly[col_val]]}
            else:
                raise ValueError("数据解析为空")
    except Exception as e: 
        print(f"中证500 PE异常: {e}")
        if "zz500_pe" in old_charts:
            new_charts["zz500_pe"] = old_charts["zz500_pe"]
            print("    [兜底] 已恢复历史 中证500 PE 数据")
    time.sleep(1)

    # 9. 沪深两市两融余额
    print("[信息] 抓取 沪深两市两融余额 ...")
    try:
        df_sh = ak.stock_margin_sse_js()
        df_sz = ak.stock_margin_szse_js()
        
        def prep(df):
            df = df.copy()
            df['dt'] = pd.to_datetime(df['日期'], errors='coerce')
            df = df.dropna(subset=['dt'])
            col_total = next((c for c in df.columns if "融资融券余额" in c), None)
            col_rz = next((c for c in df.columns if "融资余额" in c), None)
            if not col_total or not col_rz:
                raise ValueError(f"找不到两融列名，实际列名: {df.columns.tolist()}")
            df[col_total] = pd.to_numeric(df[col_total], errors='coerce')
            df[col_rz] = pd.to_numeric(df[col_rz], errors='coerce')
            return df[['dt', col_total, col_rz]].set_index('dt')
        
        sh_clean = prep(df_sh)
        sz_clean = prep(df_sz)
        
        if sh_clean is not None and sz_clean is not None:
            merged = pd.concat([sh_clean, sz_clean]).groupby('dt').sum().sort_index()
            monthly = merged.resample('ME').last().dropna().tail(13)
            if not monthly.empty:
                labels = [d.strftime('%Y-%m') for d in monthly.index]
                col_total = [c for c in sh_clean.columns if "融资融券" in c][0]
                col_rz = [c for c in sh_clean.columns if "融资余额" in c][0]
                
                new_charts["margin_balance"] = {
                    "name": "沪深两市两融余额 (亿元)", "category": "大类资产", "type": "mixed", 
                    "labels": labels,
                    "bar_data": [round(float(v) / 100000000, 2) for v in monthly[col_total]],
                    "line_data": [round(float(v) / 100000000, 2) for v in monthly[col_rz]],
                    "bar_color": "#f43f5e", "line_color": "#3b82f6"
                }
            else:
                raise ValueError("数据为空")
    except Exception as e: 
        print(f"两融余额异常: {e}")
        if "margin_balance" in old_charts:
            new_charts["margin_balance"] = old_charts["margin_balance"]
            print("    [兜底] 已恢复历史 两融余额 数据")

    os.makedirs("data", exist_ok=True)
    with open("data/macro.json", "w", encoding="utf-8") as f:
        json.dump(macro_data, f, ensure_ascii=False, indent=2)
    print(f"宏观数据完成，共 {len(new_charts)} 个图表（含兜底恢复）。")

if __name__ == "__main__":
    main()

import akshare as ak
import json
import os
import pandas as pd
import re
from datetime import datetime

# ================= 核心配置区 =================
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
    # 3. 工业与景气
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
    """模糊匹配列名，强制统一按时间排序，并提取最近N期数据"""
    try:
        col_x = [c for c in df.columns if x_col_fuzzy in c][0]
        col_y = [c for c in df.columns if y_col_fuzzy in c][0]
        
        df = df[[col_x, col_y]].copy()
        df.columns = ['date', 'value']
        
        # 清除 "---" 等非数值
        df['value'] = pd.to_numeric(df['value'], errors='coerce')
        df = df.dropna()
        
        # 【核心修复】：用正则提取年月，生成一个可排序的辅助列
        def parse_date_to_sortable(d):
            d_str = str(d)
            # 匹配 4 位数字年份，后面跟任意非数字，再跟 1-2 位数字月份
            match = re.search(r'(\d{4})\D*(\d{1,2})', d_str)
            if match:
                y, m = match.groups()
                return f"{y}-{int(m):02d}" # 格式化为 2016-01 以便字符串排序
            return d_str # 匹配失败则保留原样兜底
            
        df['sort_date'] = df['date'].apply(parse_date_to_sortable)
        
        # 按清理后的时间列进行升序排序（老数据在前，新数据在后）
        df = df.sort_values(by='sort_date').reset_index(drop=True)
        
        # 截取最后 target_len 行（即最新数据）
        df = df.tail(target_len)
        
        return {
            "labels": df['date'].tolist(), # 返回原始日期格式给前端展示
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

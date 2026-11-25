import requests
import json
import os
import re
import time
import random
from datetime import datetime, timedelta

LIST_API   = "https://reportapi.eastmoney.com/report/list"
DETAIL_URL = "https://data.eastmoney.com/report/info/{}.html"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://data.eastmoney.com/",
}

# 每类研报最多为多少篇抓摘要（抓详情要限速，别放太大）
MAX_DETAILS_STOCK    = 30   # 个股研报
MAX_DETAILS_INDUSTRY = 30   # 行业研报
FAIL_STREAK_LIMIT    = 8    # 连续失败这么多次就停手，防止被封

# 保存总量上限（个股 + 行业合计）
MAX_TOTAL_REPORTS = 80


def fetch_detail(info_code, retry=2):
    """抓单篇研报的 PC 详情页，从 HTML 里取摘要 / 页数 / 大小 / PDF 地址"""
    url = DETAIL_URL.format(info_code)
    for i in range(retry + 1):
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            r.raise_for_status()
            m = re.search(r"var zwinfo= (\{.*?\});", r.text, re.S)
            if not m:
                return None
            d = json.loads(m.group(1).replace("\\/", "/"))

            # 正文按行整理：去掉行首的全角空格缩进，丢弃空行
            raw = d.get("notice_content") or ""
            lines = [ln.strip(" \t\u3000") for ln in raw.split("\n")]
            clean = "\n".join(ln for ln in lines if ln)

            return {
                "summary": clean,
                "pages":   d.get("attach_pages") or "",
                "size":    d.get("attach_size") or "",      # 单位 KB
                "pdf":     (d.get("attach_url") or "").split("?")[0],
            }
        except Exception as e:
            if i < retry:
                time.sleep(1.0 + random.random())
            else:
                print(f"    [详情失败] {info_code}: {e}")
    return None


def fetch_eastmoney_reports(days=3, page_size=80, qtype="0", max_details=80, label="研报"):
    """拉取某一类研报（qType=0 个股 / qType=1 行业）"""
    end_time   = datetime.now().strftime("%Y-%m-%d")
    begin_time = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    params = {
        "pageSize":  page_size,
        "pageNo":    1,
        "beginTime": begin_time,
        "endTime":   end_time,
        "qType":     qtype,
        "industryCode": "*",
        "industry":     "*",
    }

    try:
        response = requests.get(LIST_API, params=params, headers=HEADERS, timeout=20)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"获取{label}列表失败: {e}")
        return []

    items = data.get("data") or []
    # 按日期倒序，保证优先给最新的抓摘要
    items.sort(key=lambda x: x.get("publishDate", ""), reverse=True)
    print(f"[信息] {label}列表拿到 {len(items)} 条（总命中 {data.get('hits')}）")

    reports, seen = [], set()
    fail_streak = 0
    stopped = False

    for idx, item in enumerate(items):
        info_code = item.get("infoCode", "")
        if not info_code or info_code in seen:
            continue
        seen.add(info_code)

        rec = {
            "title":      item.get("title", ""),
            "org":        item.get("orgSName", ""),
            "date":       (item.get("publishDate") or "")[:10],
            "infoCode":   info_code,
            "rating":     item.get("emRatingName", ""),
            "stock":      item.get("stockName", ""),
            "code":       item.get("stockCode", ""),
            "researcher": item.get("researcher", ""),
            # 个股研报用 indvInduName，行业研报用 industryName，取有值的那个
            "industry":   item.get("industryName") or item.get("indvInduName") or "",
            "pages":      item.get("attachPages") or "",
            "size":       item.get("attachSize") or "",        # KB
            "aim_price":  item.get("indvAimPriceT") or "",
            "eps_this":   item.get("predictThisYearEps") or "",
            "pe_this":    item.get("predictThisYearPe") or "",
            # 老字段，generate.py 现在读的就是它，保持不动
            "link":       f"https://data.eastmoney.com/report/info/{info_code}.html",
            # 新字段，前端详情页跳转用
            "detail":     f"report.html?id={info_code}",
            # PDF 兜底地址，抓到详情后被覆盖成精确地址
            "pdf":        f"https://pdf.dfcfw.com/pdf/H3_{info_code}_1.pdf",
            "summary":    "",
        }

        if idx < max_details and not stopped:
            d = fetch_detail(info_code)
            if d:
                rec["summary"] = d["summary"]
                rec["pdf"]     = d["pdf"] or rec["pdf"]
                rec["pages"]   = d["pages"] or rec["pages"]
                rec["size"]    = d["size"] or rec["size"]
                fail_streak = 0
            else:
                fail_streak += 1
                if fail_streak >= FAIL_STREAK_LIMIT:
                    print(f"::warning::{label}连续 {FAIL_STREAK_LIMIT} 篇摘要抓取失败，停止抓详情，仅保留列表数据")
                    stopped = True
            time.sleep(0.9 + random.random() * 0.6)

        reports.append(rec)
        if (idx + 1) % 10 == 0:
            print(f"  {label}进度 {idx + 1}/{len(items)}")

    return reports


def main():
    # 1) 个股研报
    stock_reports = fetch_eastmoney_reports(
        days=3, page_size=40, qtype="0", max_details=MAX_DETAILS_STOCK, label="个股研报"
    )
    # 2) 行业研报（产业 / 行业深度报告）
    industry_reports = fetch_eastmoney_reports(
        days=3, page_size=40, qtype="1", max_details=MAX_DETAILS_INDUSTRY, label="行业研报"
    )

    # 3) 合并去重（按 infoCode），再按日期倒序
    merged, seen_codes = [], set()
    for rec in stock_reports + industry_reports:
        key = rec.get("infoCode", "")
        if not key or key in seen_codes:
            continue
        seen_codes.add(key)
        merged.append(rec)

    merged.sort(key=lambda x: (x.get("date", ""), x.get("infoCode", "")), reverse=True)
    merged = merged[:MAX_TOTAL_REPORTS]

    os.makedirs("data", exist_ok=True)
    with open("data/reports.json", "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    ok = sum(1 for r in merged if r.get("summary"))
    n_stock = sum(1 for r in merged if r.get("stock"))
    n_industry = sum(1 for r in merged if not r.get("stock") and r.get("industry"))
    print(f"成功抓取 {len(merged)} 条研报（个股 {n_stock} / 行业 {n_industry}），其中 {ok} 条含摘要 → data/reports.json")


if __name__ == "__main__":
    main()

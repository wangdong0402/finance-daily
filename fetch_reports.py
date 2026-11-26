import requests
import json
import os
import re
import time
import random
import html as html_lib
from datetime import datetime, timedelta

LIST_API   = "https://reportapi.eastmoney.com/report/list"
DETAIL_URL = "https://data.eastmoney.com/report/info/{}.html"

# 方案A：中商情报网 产业分析频道（正文免费可读，只存摘要不转载全文）
ASKCI_LIST_URL   = "https://www.askci.com/news/chanye/"
ASKCI_SUMMARY_LEN = 500     # 摘要保留字数
ASKCI_MAX         = 15      # 每天最多取多少条

# 方案B：199IT 行业资讯（RSS 免费、含全文，只存摘要 + 跳原文，不转载正文）
IT199_FEED        = "https://www.199it.com/feed"
IT199_MAX         = 12      # 每次最多取多少条
IT199_SUMMARY_LEN = 300     # 摘要保留字数
IT199_TTL_HOURS   = 72      # 只保留最近多少小时的条目

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://data.eastmoney.com/",
}

# 每类研报最多为多少篇抓摘要（抓详情要限速，别放太大）
MAX_DETAILS_STOCK    = 30   # 个股研报
MAX_DETAILS_INDUSTRY = 30   # 行业研报
FAIL_STREAK_LIMIT    = 8    # 连续失败这么多次就停手，防止被封

# 保存总量上限（个股 + 行业 + 产业分析合计）
MAX_TOTAL_REPORTS = 110   # 2026-11 加了 199IT 后上调，保证三类都留得住


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


# ---------------------------------------------------------------- 方案A：中商情报网 产业分析

ASKCI_HEADERS = {
    "User-Agent": HEADERS["User-Agent"],
    "Referer": "https://www.askci.com/",
}


def _askci_text(url, retry=2):
    """中商返回的 header 没带 charset，必须按 utf-8 手动解码，否则中文乱码"""
    last_err = None
    for i in range(retry + 1):
        try:
            r = requests.get(url, headers=ASKCI_HEADERS, timeout=20)
            r.raise_for_status()
            return r.content.decode("utf-8", "ignore")
        except Exception as e:
            last_err = e
            if i < retry:
                time.sleep(1.0 + random.random())
    raise last_err


def _strip_tags(s):
    s = re.sub(r"<script.*?</script>", " ", s, flags=re.S)
    s = re.sub(r"<style.*?</style>", " ", s, flags=re.S)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html_lib.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def _askci_list():
    """解析产业分析频道列表：每 <li> 一篇（标题 + 行业标签 + 日期）"""
    page = _askci_text(ASKCI_LIST_URL)
    items = []
    for m in re.finditer(r"<li>(.*?)</li>", page, re.S):
        block = m.group(1)
        link_m = re.search(r'class="wes2"[^>]*href="([^"]+)"|href="([^"]+)"[^>]*class="wes2"', block)
        if not link_m:
            link_m = re.search(r'content_list_title_231.*?href="([^"]+)"', block, re.S)
        if not link_m:
            continue
        url = link_m.group(1) or link_m.group(2)
        title_m = re.search(r'class="wes2"[^>]*>(.*?)</a>', block, re.S)
        if not title_m:
            continue
        title = _strip_tags(title_m.group(1))

        date_m = re.search(r"<b>(20\d{2}-\d{2}-\d{2})</b>", block)
        date = date_m.group(1) if date_m else ""

        tag_m = re.search(r"content_list_font_232.*?title='([^']+)'", block, re.S)
        industry = tag_m.group(1) if tag_m else ""

        art_id_m = re.search(r"/(\d{6})/(\d+)\.shtml", url)
        art_id = art_id_m.group(2) if art_id_m else url

        items.append({"title": title, "url": url, "date": date, "industry": industry, "art_id": art_id})

    uniq, seen = [], set()
    for it in items:
        if it["url"] in seen:
            continue
        seen.add(it["url"])
        uniq.append(it)
    return uniq


def _askci_summary(url):
    """返回 (摘要, 来源机构)"""
    page = _askci_text(url)
    org_m = re.search(r"来源：([^<<]+)</span>", page)
    org = org_m.group(1).strip() if org_m else "中商情报网"

    i = page.find("detail_content_text")
    if i < 0:
        return "", org
    seg = page[i:i + 20000]
    j = seg.find('<div class="clear">')
    body = seg[:j] if j > 0 else seg[:15000]
    body = re.sub(r'detail_content_text">', " ", body, count=1)
    return _strip_tags(body)[:ASKCI_SUMMARY_LEN], org


def fetch_askci_analysis(limit=ASKCI_MAX):
    """抓中商情报网产业分析（正文免费，只存摘要 + 跳原文）"""
    try:
        items = _askci_list()
    except Exception as e:
        print(f"::warning::中商情报网 列表抓取失败: {e}")
        return []

    print(f"[信息] 产业分析列表拿到 {len(items)} 条（去重后）")
    if not items:
        print("::warning::中商情报网 列表解析到 0 条，页面结构可能已改版")
        return []

    out = []
    for it in items[:limit]:
        try:
            summary, org = _askci_summary(it["url"])
        except Exception as e:
            print(f"  [详情失败] {it['url']}: {e}")
            summary, org = "", "中商情报网"

        rec = {
            "title":      it["title"],
            "org":        org,
            "date":       it["date"],
            "infoCode":   it["art_id"],
            "rating":     "",
            "stock":      "",
            "code":       "",
            "researcher": "",
            "industry":   it["industry"],
            "pages":      "",
            "size":       "",
            "aim_price":  "",
            "eps_this":   "",
            "pe_this":    "",
            "link":       it["url"],
            # 中商文章不进自建详情页，直接跳原文
            "detail":     it["url"],
            "pdf":        "",
            "summary":    summary,
            "reportType": "产业分析",
        }
        out.append(rec)
        print(f"  √ {it['date']} [{it['industry']}] {it['title'][:36]} | 摘要 {len(summary)} 字")
        time.sleep(0.8 + random.random() * 0.5)

    return out


# ---------------------------------------------------------------- 方案B：199IT 行业资讯
def _html_to_text(s):
    """HTML 正文转纯文本"""
    if not s:
        return ""
    s = re.sub(r"<script.*?</script>", " ", s, flags=re.S | re.I)
    s = re.sub(r"<style.*?</style>", " ", s, flags=re.S | re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html_lib.unescape(s)
    return re.sub(r"[\s\u3000]+", " ", s).strip()


IT199_GENERIC_TAGS = {"199IT推荐文章", "199IT数据", "199IT原创", "199IT", "研究报告", "数据", "统计"}


def _it199_org(title, tags=None):
    """卡片主体文字：优先标题里的机构名（Eurostat：…），否则用分类里的主题标签"""
    m = re.match(r"^\s*([^：:]{2,18})[：:]", title or "")
    if m:
        cand = m.group(1).strip()
        too_generic = re.search(r"报告|数据|分析|研究|统计|年度|月度|季度|展望|趋势|白皮书|盘点", cand)
        looks_like_year = re.match(r"^\d{4}\s*年|^\d{2,4}年", cand)
        if not too_generic and not looks_like_year and 2 <= len(cand) <= 12:
            return cand
    for t in (tags or []):
        t = t.strip()
        if t and t not in IT199_GENERIC_TAGS and 2 <= len(t) <= 14:
            return t
    return "行业资讯"


def _it199_summary(text):
    """199IT 的「数据图表」类正文只有一串『更多阅读』相关链接，没有实质内容 → 不存摘要"""
    text = (text or "").strip()
    if not text:
        return ""
    if text.startswith("更多阅读"):
        return ""
    return text[:IT199_SUMMARY_LEN]


def fetch_199it(limit=IT199_MAX):
    """抓 199IT RSS：免费全文源，但本站只存摘要和原文链接"""
    import feedparser

    try:
        r = requests.get(IT199_FEED, headers={"User-Agent": HEADERS["User-Agent"]}, timeout=25)
        r.raise_for_status()
        feed = feedparser.parse(r.content)
    except Exception as e:
        print(f"::warning::199IT RSS 抓取失败: {e}")
        return []

    entries = getattr(feed, "entries", []) or []
    print(f"[信息] 199IT RSS 拿到 {len(entries)} 条")
    if not entries:
        print("::warning::199IT RSS 解析到 0 条，源可能异常")
        return []

    cutoff = datetime.now() - timedelta(hours=IT199_TTL_HOURS)
    out = []
    for e in entries:
        if len(out) >= limit:
            break
        title = _html_to_text(e.get("title", ""))
        title = re.sub(r"[\u200b\u200c\u200d\u2060\ufeff]", "", title).strip()
        link = e.get("link", "") or ""
        if not title or not link:
            continue

        pub = e.get("published_parsed")
        if pub:
            utc_dt = datetime(*pub[:6])
            if utc_dt < cutoff:
                continue
            date_str = (utc_dt + timedelta(hours=8)).strftime("%Y-%m-%d")
        else:
            date_str = datetime.now().strftime("%Y-%m-%d")

        body = ""
        if e.get("content"):
            body = " ".join(c.get("value", "") for c in e["content"])
        body = _html_to_text(body or e.get("summary", ""))
        summary = _it199_summary(body)
        if not summary:
            # 「数据图表」类条目正文只有一串相关链接，没有实质内容，直接跳过
            continue

        tags = [c.get("term", "") for c in (e.get("tags") or [])]
        org = _it199_org(title, tags)
        out.append({
            "title":      title,
            "org":        "199IT",
            "date":       date_str,
            "infoCode":   link,
            "rating":     "",
            "stock":      "",
            "code":       "",
            "researcher": "",
            "industry":   org,       # 卡片主体位置显示机构名（Eurostat / Gartner…）
            "pages":      "",
            "size":       "",
            "aim_price":  "",
            "eps_this":   "",
            "pe_this":    "",
            "link":       link,
            "detail":     link,      # 不进自建详情页，直接跳原文
            "pdf":        "",
            "summary":    summary,
            "reportType": "产业分析",
        })
        print(f"  √ {date_str} [{org}] {title[:36]} | 摘要 {len(summary)} 字")

    if not out:
        print("::warning::199IT 这次没有抓到带正文的条目（可能全是数据图表），不影响其它研报")
    return out


def main():
    # 1) 个股研报
    stock_reports = fetch_eastmoney_reports(
        days=3, page_size=40, qtype="0", max_details=MAX_DETAILS_STOCK, label="个股研报"
    )
    # 2) 行业研报（产业 / 行业深度报告）
    industry_reports = fetch_eastmoney_reports(
        days=3, page_size=40, qtype="1", max_details=MAX_DETAILS_INDUSTRY, label="行业研报"
    )
    # 3) 产业分析（中商情报网）
    analysis_reports = fetch_askci_analysis()
    # 3b) 产业分析（199IT 行业资讯）
    it199_reports = fetch_199it()

    # 4) 合并去重（按 infoCode），再按日期倒序
    merged, seen_codes = [], set()
    for rec in stock_reports + industry_reports + analysis_reports + it199_reports:
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
    n_industry = sum(1 for r in merged if (not r.get("stock")) and r.get("industry") and r.get("reportType") != "产业分析")
    n_analysis = sum(1 for r in merged if r.get("reportType") == "产业分析")
    print(f"成功抓取 {len(merged)} 条研报（个股 {n_stock} / 行业 {n_industry} / 产业分析 {n_analysis}），"
          f"其中 {ok} 条含摘要 → data/reports.json")


if __name__ == "__main__":
    main()

import os
import re
import json
import html
from datetime import datetime, timezone

import yaml
import feedparser
import requests

SOURCES_FILE = "sources.yaml"
OUTPUT_FILE = "data/news.json"
MAX_PER_SOURCE = 15
MAX_TOTAL = 100

# 伪装成正常的浏览器，防止被部分网站当作爬虫拦截
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def clean_text(text):
    if not text:
        return ""
    text = html.unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:300]

def parse_time(entry):
    for key in ("published_parsed", "updated_parsed"):
        value = entry.get(key)
        if value:
            try:
                dt = datetime(*value[:6], tzinfo=timezone.utc)
                return dt.isoformat()
            except Exception:
                pass
    return datetime.now(timezone.utc).isoformat()

def fetch_source(source):
    name = source.get("name", "未知来源")
    url = source.get("url", "")
    category = source.get("category", "未分类")
    items = []

    if not url:
        return items

    try:
        # 使用 requests 带上伪装头去获取内容，再交由 feedparser 解析
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        feed = feedparser.parse(response.content)
        
        if feed.bozo:
            print(f"[警告] {name}: 解析可能有问题，尝试读取")
            
        entries = feed.entries[:MAX_PER_SOURCE]
        for entry in entries:
            title = clean_text(entry.get("title", ""))
            link = entry.get("link", "")
            summary = clean_text(entry.get("summary", entry.get("description", "")))
            if not title or not link:
                continue
            items.append({
                "title": title,
                "link": link,
                "summary": summary,
                "source": name,
                "category": category,
                "published": parse_time(entry),
            })
        print(f"[成功] {name}: 抓到 {len(items)} 条")
    except Exception as exc:
        print(f"[失败] {name}: {exc}")

    return items

def main():
    with open(SOURCES_FILE, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}

    sources = config.get("sources", [])
    all_items = []

    for source in sources:
        all_items.extend(fetch_source(source))

    seen = set()
    unique_items = []
    for item in all_items:
        link = item["link"]
        if link in seen:
            continue
        seen.add(link)
        unique_items.append(item)

    unique_items.sort(key=lambda x: x["published"], reverse=True)
    unique_items = unique_items[:MAX_TOTAL]

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "updated": datetime.now(timezone.utc).isoformat(),
            "count": len(unique_items),
            "items": unique_items,
        }, f, ensure_ascii=False, indent=2)

    print(f"完成：共写入 {len(unique_items)} 条到 {OUTPUT_FILE}")

if __name__ == "__main__":
    main()

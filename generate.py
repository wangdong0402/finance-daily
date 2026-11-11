import json
import os
import html
from datetime import datetime

DATA_FILE = "data/news.json"
OUTPUT_FILE = "dist/index.html"


def format_time(value):
    if not value:
        return ""
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(value)[:16]


def load_data():
    if not os.path.exists(DATA_FILE):
        return {"updated": "", "count": 0, "items": []}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def build_cards(items):
    if not items:
        return '<div class="empty">还没有数据。请等待每日自动任务运行，或手动运行 fetch.py 后再生成。</div>'

    cards = []
    for item in items:
        title = html.escape(item.get("title", ""))
        link = html.escape(item.get("link", ""))
        summary = html.escape(item.get("summary", ""))
        source = html.escape(item.get("source", ""))
        category = html.escape(item.get("category", ""))
        published = html.escape(format_time(item.get("published", "")))
        
        # 为不同的分类添加不同的颜色标签
        tag_color = ""
        if "宏观" in category or "政策" in category:
            tag_color = "background: #fee2e2; color: #991b1b;"  # 红色系
        elif "科技" in category or "商业" in category:
            tag_color = "background: #dbeafe; color: #1e40af;"  # 蓝色系
        else:
            tag_color = "background: #f3f4f6; color: #374151;"  # 灰色系

        summary_html = f'<p class="summary">{summary}</p>' if summary else ""

        cards.append(f'''
        <article class="card">
          <div class="meta">
            <span class="tag" style="{tag_color}">{category}</span>
            <span>{source}</span>
            <span>{published}</span>
          </div>
          <h2><a href="{link}" target="_blank" rel="noopener noreferrer">{title}</a></h2>
          {summary_html}
        </article>''')

    return "\n".join(cards)


def main():
    data = load_data()
    items = data.get("items", [])
    updated = format_time(data.get("updated", ""))
    count = data.get("count", len(items))
    cards = build_cards(items)

    html_doc = f'''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>每日财经</title>
<style>
:root {{ color-scheme: light dark; }}
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "PingFang SC", "Microsoft YaHei", sans-serif;
  background: #f5f5f7;
  color: #1d1d1f;
}}
header {{
  position: sticky;
  top: 0;
  backdrop-filter: blur(12px);
  background: rgba(245, 245, 247, .85);
  border-bottom: 1px solid rgba(0, 0, 0, .08);
  padding: 16px 16px 12px;
  z-index: 100;
}}
.header-top {{ display: flex; justify-content: space-between; align-items: flex-start; }}
h1 {{ font-size: 20px; margin: 0 0 4px; }}
.sub {{ font-size: 12px; color: #6e6e73; }}
main {{ padding: 12px 12px 32px; max-width: 760px; margin: 0 auto; }}
.card {{
  background: #fff;
  border-radius: 14px;
  padding: 14px 16px;
  margin-bottom: 12px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, .04);
}}
.meta {{
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  font-size: 12px;
  color: #6e6e73;
  margin-bottom: 6px;
}}
.tag {{
  border-radius: 999px;
  padding: 2px 8px;
  font-weight: 500;
}}
h2 {{ font-size: 16px; line-height: 1.45; margin: 0 0 6px; }}
h2 a {{ color: inherit; text-decoration: none; }}
h2 a:hover {{ text-decoration: underline; }}
.summary {{ font-size: 14px; line-height: 1.6; color: #3a3a3c; margin: 0; }}
.empty {{
  background: #fff;
  border-radius: 14px;
  padding: 32px 20px;
  text-align: center;
  color: #6e6e73;
  font-size: 14px;
}}

@media (prefers-color-scheme: dark) {{
  body {{ background: #000; color: #f5f5f7; }}
  header {{ background: rgba(0, 0, 0, .8); border-bottom-color: rgba(255, 255, 255, .12); }}
  .sub, .meta {{ color: #98989d; }}
  .card, .empty {{ background: #1c1c1e; box-shadow: none; }}
  .summary {{ color: #d1d1d6; }}
}}
</style>
</head>
<body>
<header>
  <div class="header-top">
    <div>
      <h1>每日财经</h1>
      <div class="sub">更新：{updated or "暂无"} · 共 {count} 条</div>
    </div>
  </div>
</header>
<main>
{cards}
</main>
</body>
</html>'''

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html_doc)

    print(f"已生成 {OUTPUT_FILE}，共 {len(items)} 条")


if __name__ == "__main__":
    main()

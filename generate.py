import json
import os
import html
from datetime import datetime

NEWS_FILE = "data/news.json"
REPORTS_FILE = "data/reports.json"
SENTIMENT_FILE = "data/sentiment.json"
OUTPUT_FILE = "dist/index.html"


def format_time(value):
    if not value:
        return ""
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(value)[:16]


def load_json(filepath, default):
    if not os.path.exists(filepath):
        return default
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def build_news_cards(items):
    if not items:
        return '<div class="empty">还没有新闻数据。</div>'
    cards = []
    for item in items:
        title = html.escape(item.get("title", ""))
        link = html.escape(item.get("link", ""))
        summary = html.escape(item.get("summary", ""))
        source = html.escape(item.get("source", ""))
        category = html.escape(item.get("category", ""))
        published = html.escape(format_time(item.get("published", "")))
        tag_style = ""
        if "宏观" in category or "政策" in category:
            tag_style = "background: #fee2e2; color: #991b1b;"
        elif "国际财经" in category:
            tag_style = "background: #dcfce7; color: #166534;"
        elif "数据" in category:
            tag_style = "background: #f3e8ff; color: #6b21a8;"
        elif "投资" in category:
            tag_style = "background: #fef3c7; color: #92400e;"
        elif "产业" in category or "商业" in category or "科技" in category:
            tag_style = "background: #dbeafe; color: #1e40af;"
        else:
            tag_style = "background: #f3f4f6; color: #374151;"
        summary_html = f'<p class="summary">{summary}</p>' if summary else ""
        cards.append(f'''
        <article class="card">
          <div class="meta">
            <span class="tag" style="{tag_style}">{category}</span>
            <span>{source}</span>
            <span>{published}</span>
          </div>
          <h2><a href="{link}" target="_blank" rel="noopener noreferrer">{title}</a></h2>
          {summary_html}
        </article>''')
    return "\n".join(cards)


def build_report_cards(reports):
    if not reports:
        return '<div class="empty">还没有研报数据。</div>'
    cards = []
    for item in reports:
        title = html.escape(item.get("title", ""))
        link = html.escape(item.get("link", ""))
        org = html.escape(item.get("org", ""))
        date = html.escape(item.get("date", ""))
        rating = html.escape(item.get("rating", ""))
        stock = html.escape(item.get("stock", ""))
        code = html.escape(item.get("code", ""))
        rating_color = "#6e6e73"
        if "买入" in rating or "推荐" in rating:
            rating_color = "#dc2626"
        elif "增持" in rating:
            rating_color = "#ea580c"
        elif "中性" in rating or "持有" in rating:
            rating_color = "#2563eb"
        rating_html = f'<span style="color: {rating_color}; font-weight: bold; margin-left: 8px;">[{rating}]</span>' if rating else ""
        cards.append(f'''
        <article class="card">
          <div class="meta">
            <span class="tag" style="background: #e0e7ff; color: #3730a3;">研报</span>
            <span style="font-weight: bold; color: #1d1d1f;">{stock} ({code})</span>
            <span>{org}</span>
            <span>{date}</span>
          </div>
          <h2><a href="{link}" target="_blank" rel="noopener noreferrer">{title}</a>{rating_html}</h2>
        </article>''')
    return "\n".join(cards)


def build_sector_rows(sectors):
    rows = ""
    for s in sectors:
        name = html.escape(s.get("name", ""))
        net = s.get("main_net", 0)
        days = s.get("days", "")
        net_color = "#ef4444" if net > 0 else "#10b981" if net < 0 else "#6b7280"
        net_text = f"+{net} 亿" if net > 0 else f"{net} 亿"
        days_hint = f'<span style="font-size:11px;color:#98989d;margin-left:4px;">({days}日)</span>' if days else ""
        rows += f'''
        <div style="display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #eee;">
          <div style="flex: 1; font-size: 13px; color: #1d1d1f;">{name}{days_hint}</div>
          <div style="font-size: 13px; font-weight: bold; color: {net_color};">{net_text}</div>
        </div>'''
    return rows or '<div style="color: #98989d; font-size: 12px; padding: 12px 0;">暂无数据</div>'


def build_sentiment_html(data):
    if not data or not data.get("periods"):
        return '<div class="empty">还没有市场情绪数据。</div>'

    updated = html.escape(data.get("updated", ""))
    periods = data["periods"]

    period_labels = {"5d": "5个交易日", "20d": "20个交易日", "60d": "60个交易日"}
    blocks = ""
    for key in ["60d", "20d", "5d"]:
        p = periods.get(key, {})
        inflow = p.get("inflow", [])
        outflow = p.get("outflow", [])
        title = period_labels.get(key, key)
        blocks += f'''
        <div style="margin-bottom: 32px;">
          <div style="font-size: 16px; font-weight: bold; color: #1d1d1f; margin-bottom: 12px; padding-left: 8px; border-left: 4px solid #1d1d1f;">
            📅 {title} · 行业累计资金流向
          </div>
          <div style="display: flex; gap: 12px;">
            <div style="flex: 1; background: #fff; border-radius: 12px; padding: 14px;">
              <div style="font-size: 13px; font-weight: bold; color: #ef4444; margin-bottom: 8px;">流入 TOP10</div>
              {build_sector_rows(inflow)}
            </div>
            <div style="flex: 1; background: #fff; border-radius: 12px; padding: 14px;">
              <div style="font-size: 13px; font-weight: bold; color: #10b981; margin-bottom: 8px;">流出 TOP10</div>
              {build_sector_rows(outflow)}
            </div>
          </div>
        </div>'''

    return f'''
    <div class="sentiment-dashboard">
      <div class="sentiment-time">数据更新于：{updated}（行业资金流为盘后数据）</div>
      {blocks}
    </div>
    '''


def main():
    news_data = load_json(NEWS_FILE, {"updated": "", "count": 0, "items": []})
    reports_data = load_json(REPORTS_FILE, [])
    sentiment_data = load_json(SENTIMENT_FILE, {})

    news_items = news_data.get("items", [])
    news_updated = format_time(news_data.get("updated", ""))
    news_count = news_data.get("count", len(news_items))

    news_cards_html = build_news_cards(news_items)
    reports_cards_html = build_report_cards(reports_data)
    sentiment_cards_html = build_sentiment_html(sentiment_data)

    html_doc = f'''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>个人财经终端</title>
<style>
:root {{ color-scheme: light dark; }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "PingFang SC", "Microsoft YaHei", sans-serif; background: #f5f5f7; color: #1d1d1f; }}
header {{ position: sticky; top: 0; backdrop-filter: blur(12px); background: rgba(245, 245, 247, .85); border-bottom: 1px solid rgba(0, 0, 0, .08); padding: 16px 16px 0; z-index: 100; }}
.header-top {{ margin-bottom: 12px; }}
h1 {{ font-size: 20px; margin: 0 0 4px; }}
.sub {{ font-size: 12px; color: #6e6e73; }}
.tabs {{ display: flex; gap: 20px; overflow-x: auto; }}
.tab-btn {{ background: none; border: none; padding: 10px 0; font-size: 16px; font-weight: bold; color: #6e6e73; cursor: pointer; border-bottom: 3px solid transparent; transition: all 0.2s; white-space: nowrap; }}
.tab-btn.active {{ color: #1d1d1f; border-bottom-color: #1d1d1f; }}
main {{ padding: 12px 12px 32px; max-width: 760px; margin: 0 auto; }}
.card {{ background: #fff; border-radius: 14px; padding: 14px 16px; margin-bottom: 12px; box-shadow: 0 1px 2px rgba(0, 0, 0, .04); }}
.meta {{ display: flex; flex-wrap: wrap; gap: 8px; align-items: center; font-size: 12px; color: #6e6e73; margin-bottom: 6px; }}
.tag {{ border-radius: 999px; padding: 2px 8px; font-weight: 500; }}
h2 {{ font-size: 16px; line-height: 1.45; margin: 0 0 6px; }}
h2 a {{ color: inherit; text-decoration: none; }}
h2 a:hover {{ text-decoration: underline; }}
.summary {{ font-size: 14px; line-height: 1.6; color: #3a3a3c; margin: 0; }}
.empty {{ background: #fff; border-radius: 14px; padding: 32px 20px; text-align: center; color: #6e6e73; font-size: 14px; }}
.sentiment-dashboard {{ background: transparent; }}
.sentiment-time {{ text-align: center; font-size: 12px; color: #98989d; margin-bottom: 20px; }}
@media (prefers-color-scheme: dark) {{
  body {{ background: #000; color: #f5f5f7; }}
  header {{ background: rgba(0, 0, 0, .8); border-bottom-color: rgba(255, 255, 255, .12); }}
  .sub, .meta {{ color: #98989d; }}
  .card, .empty {{ background: #1c1c1e; box-shadow: none; }}
  .summary {{ color: #d1d1d6; }}
  .tab-btn {{ color: #98989d; }}
  .tab-btn.active {{ color: #f5f5f7; border-bottom-color: #f5f5f7; }}
  .meta span[style*="color: #1d1d1f;"] {{ color: #f5f5f7 !important; }}
  .sentiment-dashboard div[style*="background: #fff;"] {{ background: #1c1c1e !important; }}
  .sentiment-dashboard div[style*="border-left: 4px solid #1d1d1f;"] {{ border-left-color: #f5f5f7 !important; }}
  .sentiment-dashboard div[style*="color: #1d1d1f;"] {{ color: #f5f5f7 !important; }}
}}
</style>
</head>
<body>
<header>
  <div class="header-top">
    <h1>个人财经终端</h1>
    <div class="sub">更新：{news_updated or "暂无"} · 共 {news_count} 条新闻</div>
  </div>
  <div class="tabs">
    <button class="tab-btn active" onclick="switchTab('news')" id="btn-news">每日新闻</button>
    <button class="tab-btn" onclick="switchTab('reports')" id="btn-reports">券商研报</button>
    <button class="tab-btn" onclick="switchTab('sentiment')" id="btn-sentiment">市场情绪</button>
  </div>
</header>
<main>
  <div id="tab-news">{news_cards_html}</div>
  <div id="tab-reports" style="display: none;">{reports_cards_html}</div>
  <div id="tab-sentiment" style="display: none;">{sentiment_cards_html}</div>
</main>
<script>
function switchTab(tab) {{
  ['news','reports','sentiment'].forEach(t => {{
    document.getElementById('tab-' + t).style.display = 'none';
    document.getElementById('btn-' + t).classList.remove('active');
  }});
  document.getElementById('tab-' + tab).style.display = 'block';
  document.getElementById('btn-' + tab).classList.add('active');
}}
</script>
</body>
</html>'''

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html_doc)
    print(f"已生成 {OUTPUT_FILE}。")


if __name__ == "__main__":
    main()

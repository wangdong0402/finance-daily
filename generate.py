import json
import os
import html
from datetime import datetime

NEWS_FILE = "data/news.json"
REPORTS_FILE = "data/reports.json"
SENTIMENT_FILE = "data/sentiment.json"
MACRO_FILE = "data/macro.json"
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
        change = s.get("change", 0)
        net = s.get("main_net", 0)
        net_color = "#ef4444" if net > 0 else "#10b981" if net < 0 else "#6b7280"
        net_text = f"+{net} 亿" if net > 0 else f"{net} 亿"
        rows += f'''
        <div style="display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #eee;">
          <div style="flex: 1; font-size: 13px; color: #1d1d1f;">{name} <span style="font-size:11px;color:#98989d;">({change:+.2f}%)</span></div>
          <div style="font-size: 13px; font-weight: bold; color: {net_color};">{net_text}</div>
        </div>'''
    return rows or '<div style="color: #98989d; font-size: 12px; padding: 12px 0;">暂无数据</div>'


def build_sentiment_html(data):
    if not data or not data.get("periods"):
        return '<div class="empty">还没有市场情绪数据。</div>'

    updated = html.escape(data.get("updated", ""))
    periods = data["periods"]

    period_labels = {"20d": "20个交易日", "10d": "10个交易日", "5d": "5个交易日"}
    blocks = ""
    for key in ["20d", "10d", "5d"]:
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
      <div class="sentiment-time">数据更新于：{updated}（同花顺行业资金流，盘后数据）</div>
      {blocks}
    </div>
    '''


def build_macro_html(macro_data):
    charts = macro_data.get("charts", {})
    categories = {"货币": "💵 货币与信用", "物价": "📈 物价与通胀", "工业": "🏭 工业与景气", "外贸": "🏗️ 投资与外贸"}
    
    # 生成二级分类导航栏
    cat_nav = ""
    first_cat = True
    for cat_id, cat_name in categories.items():
        # 检查该分类下是否有数据
        if any(c["category"] == cat_id for c in charts.values()):
            active = "active" if first_cat else ""
            cat_nav += f'<button class="sub-tab-btn {active}" onclick="switchSubTab(\'{cat_id}\')" id="subbtn-{cat_id}">{cat_name}</button>'
            first_cat = False

    # 生成各个分类的内容区
    cat_contents = ""
    first_content = True
    for cat_id in categories.keys():
        if not any(c["category"] == cat_id for c in charts.values()):
            continue
            
        display = "block" if first_content else "none"
        first_content = False
        
        charts_html = ""
        for key, cfg in charts.items():
            if cfg["category"] != cat_id:
                continue
                
            if cfg["type"] in ("line", "bar"):
                charts_html += f'''
                <div class="macro-card">
                  <h3>{cfg['name']}</h3>
                  <div style="position: relative; height: 200px; width: 100%;">
                    <canvas id="chart-{key}"></canvas>
                  </div>
                </div>'''
            elif cfg["type"] == "multi_line":
                charts_html += f'''
                <div class="macro-card">
                  <h3>{cfg['name']}</h3>
                  <div style="position: relative; height: 200px; width: 100%;">
                    <canvas id="chart-{key}"></canvas>
                  </div>
                </div>'''
        
        cat_contents += f'<div id="subtab-{cat_id}" class="sub-tab-content" style="display: {display};">{charts_html}</div>'

    return f'''
    <div class="macro-wrapper">
      <div class="sub-tabs">{cat_nav}</div>
      <div class="sub-tab-container">{cat_contents}</div>
    </div>
    '''


def main():
    news_data = load_json(NEWS_FILE, {"updated": "", "count": 0, "items": []})
    reports_data = load_json(REPORTS_FILE, [])
    sentiment_data = load_json(SENTIMENT_FILE, {})
    macro_data = load_json(MACRO_FILE, {"charts": {}})

    news_items = news_data.get("items", [])
    news_updated = format_time(news_data.get("updated", ""))
    news_count = news_data.get("count", len(news_items))

    news_cards_html = build_news_cards(news_items)
    reports_cards_html = build_report_cards(reports_data)
    sentiment_cards_html = build_sentiment_html(sentiment_data)
    macro_cards_html = build_macro_html(macro_data)

    macro_json_str = json.dumps(macro_data.get("charts", {}), ensure_ascii=False)

    html_doc = f'''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>个人财经终端</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
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

/* 宏观二级菜单样式 */
.macro-wrapper {{ background: transparent; }}
.sub-tabs {{ display: flex; gap: 10px; overflow-x: auto; margin-bottom: 16px; padding-bottom: 4px; }}
.sub-tab-btn {{ background: rgba(0,0,0,0.05); border: none; padding: 8px 16px; border-radius: 20px; font-size: 13px; font-weight: 500; color: #3a3a3c; cursor: pointer; white-space: nowrap; }}
.sub-tab-btn.active {{ background: #1d1d1f; color: #fff; }}
.macro-card {{ background: #fff; border-radius: 14px; padding: 16px; box-shadow: 0 1px 2px rgba(0, 0, 0, .04); margin-bottom: 16px; }}
.macro-card h3 {{ font-size: 14px; margin: 0 0 16px 0; color: #3a3a3c; }}

@media (prefers-color-scheme: dark) {{
  body {{ background: #000; color: #f5f5f7; }}
  header {{ background: rgba(0, 0, 0, .8); border-bottom-color: rgba(255, 255, 255, .12); }}
  .sub, .meta {{ color: #98989d; }}
  .card, .empty, .macro-card {{ background: #1c1c1e; box-shadow: none; }}
  .summary {{ color: #d1d1d6; }}
  .macro-card h3 {{ color: #f5f5f7; }}
  .tab-btn {{ color: #98989d; }}
  .tab-btn.active {{ color: #f5f5f7; border-bottom-color: #f5f5f7; }}
  .sub-tab-btn {{ background: rgba(255,255,255,0.1); color: #d1d1d6; }}
  .sub-tab-btn.active {{ background: #f5f5f7; color: #000; }}
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
    <button class="tab-btn" onclick="switchTab('macro')" id="btn-macro">宏观数据</button>
  </div>
</header>
<main>
  <div id="tab-news">{news_cards_html}</div>
  <div id="tab-reports" style="display: none;">{reports_cards_html}</div>
  <div id="tab-sentiment" style="display: none;">{sentiment_cards_html}</div>
  <div id="tab-macro" style="display: none;">{macro_cards_html}</div>
</main>

<script>
const macroData = {macro_json_str};
const chartInstances = {{}};

function switchTab(tab) {{
  ['news','reports','sentiment','macro'].forEach(t => {{
    document.getElementById('tab-' + t).style.display = 'none';
    document.getElementById('btn-' + t).classList.remove('active');
  }});
  document.getElementById('tab-' + tab).style.display = 'block';
  document.getElementById('btn-' + tab).classList.add('active');
  if(tab === 'macro') lazyRenderCharts();
}}

function switchSubTab(catId) {{
  document.querySelectorAll('.sub-tab-content').forEach(el => el.style.display = 'none');
  document.querySelectorAll('.sub-tab-btn').forEach(el => el.classList.remove('active'));
  document.getElementById('subtab-' + catId).style.display = 'block';
  document.getElementById('subbtn-' + catId).classList.add('active');
  lazyRenderCharts();
}}

// 懒加载图表渲染机制
function lazyRenderCharts() {{
  const isDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  const textColor = isDark ? '#98989d' : '#6e6e73';
  const gridColor = isDark ? '#3a3a3c' : '#e5e7eb';

  // 只绘制当前可见的子 Tab 里的图表
  const activeContent = document.querySelector('.sub-tab-content[style*="display: block"]');
  if (!activeContent) return;

  activeContent.querySelectorAll('canvas').forEach(canvas => {{
    const chartId = canvas.id.replace('chart-', '');
    if (chartInstances[chartId]) return; // 已经画过了就跳过

    const cfg = macroData[chartId];
    if (!cfg) return;

    let datasets = [];
    let chartType = cfg.type === 'multi_line' ? 'line' : cfg.type;

    if (cfg.type === 'multi_line') {{
      datasets = cfg.series.map(s => ({{
        label: s.name, data: s.data, borderColor: s.color, backgroundColor: s.color + '20',
        borderWidth: 2, tension: 0.3, pointRadius: 2, fill: false
      }}));
    }} else if (cfg.type === 'bar') {{
      // 为柱状图配置正负数不同颜色
      const bgColors = cfg.data.map(v => v >= 0 ? cfg.color : '#10b981');
      datasets = [{{
        data: cfg.data, backgroundColor: bgColors, borderRadius: 4
      }}];
    }} else {{
      datasets = [{{
        data: cfg.data, borderColor: cfg.color, backgroundColor: cfg.color + '20',
        borderWidth: 2, tension: 0.3, pointRadius: 3, fill: true
      }}];
    }}

    const config = {{
      type: chartType,
      data: {{ labels: cfg.labels, datasets: datasets }},
      options: {{
        responsive: true, maintainAspectRatio: false,
        plugins: {{ 
          legend: {{ display: cfg.type === 'multi_line', position: 'top', labels: {{ boxWidth: 12, font: {{ size: 10 }} }} }},
          tooltip: {{ mode: 'index', intersect: false }}
        }},
        scales: {{
          x: {{ grid: {{ display: false }}, ticks: {{ color: textColor, maxRotation: 45, minRotation: 45, font: {{ size: 10 }} }} }},
          y: {{ grid: {{ color: gridColor, drawBorder: false }}, ticks: {{ color: textColor, font: {{ size: 10 }} }} }}
        }}
      }}
    }};

    // 如果是 PMI，添加 50 枯荣线
    if (cfg.baseline) {{
      config.options.plugins.annotation = {{
        annotations: {{
          line1: {{
            type: 'line', yMin: cfg.baseline, yMax: cfg.baseline,
            borderColor: '#ef4444', borderWidth: 1, borderDash: [5, 5],
            label: {{ display: true, content: '枯荣线', position: 'end' }}
          }}
        }}
      }};
    }}

    chartInstances[chartId] = new Chart(canvas.getContext('2d'), config);
  }});
}}

// 每次点开宏观 Tab 时，顺便检查并渲染一次
document.addEventListener('DOMContentLoaded', () => {{
  // 延迟一下确保 DOM 完全就绪
  setTimeout(lazyRenderCharts, 500);
}});
</script>
</body>
</html>'''
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html_doc)
    print(f"已生成 {OUTPUT_FILE}，包含二级菜单和懒加载图表。")


if __name__ == "__main__":
    main()

import json
import os
import html
from datetime import datetime, timezone, timedelta

NEWS_FILE = "data/news.json"
REPORTS_FILE = "data/reports.json"
SENTIMENT_FILE = "data/sentiment.json"
MACRO_FILE = "data/macro.json"
OUTPUT_FILE = "dist/index.html"


def format_relative_time(value):
    """将时间转换为相对时间（如：2小时前、昨天 14:30）"""
    if not value:
        return ""
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        diff = now - dt
        if diff.total_seconds() < 0:
            return "刚刚"
        
        if diff.days == 0:
            if diff.seconds < 3600:
                return f"{diff.seconds // 60} 分钟前"
            return f"{diff.seconds // 3600} 小时前"
        elif diff.days == 1:
            # 转为北京时间显示
            local_dt = dt + timedelta(hours=8)
            return f"昨天 {local_dt.strftime('%H:%M')}"
        else:
            local_dt = dt + timedelta(hours=8)
            return local_dt.strftime('%m-%d %H:%M')
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
    
    # 提取所有分类
    categories = sorted(list(set(item.get("category", "") for item in items if item.get("category"))))
    
    # 构建分类筛选栏
    filter_html = '<div class="filter-bar" id="filter-bar">'
    filter_html += f'<button class="filter-btn active" onclick="filterNews(\'all\', this)">全部</button>'
    for cat in categories:
        filter_html += f'<button class="filter-btn" onclick="filterNews(\'{cat}\', this)">{cat}</button>'
    filter_html += '</div>'

    cards = []
    last_date_key = None
    today_local = (datetime.now(timezone.utc) + timedelta(hours=8)).date()
    weekday_cn = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    for item in items:
        # 按北京时间日期分组，插入日期分隔标签
        date_key = None
        try:
            _dt = datetime.fromisoformat(item.get("published", "").replace("Z", "+00:00"))
            _local = (_dt + timedelta(hours=8)).date()
            # 未来时间戳（源站时区提前）统一归到当天，避免出现"明天的分组"
            if _local > (datetime.now(timezone.utc) + timedelta(hours=8)).date():
                _local = (datetime.now(timezone.utc) + timedelta(hours=8)).date()
            date_key = _local
        except Exception:
            date_key = None
        if date_key != last_date_key:
            last_date_key = date_key
            if date_key is not None:
                delta_days = (today_local - date_key).days
                label_date = f"{date_key.month}月{date_key.day}日"
                if delta_days == 0:
                    group_label = f"今天 · {label_date}"
                elif delta_days == 1:
                    group_label = f"昨天 · {label_date}"
                else:
                    group_label = f"{label_date} {weekday_cn[date_key.weekday()]}"
                cards.append(f'<div class="date-group">{group_label}</div>')

        title = html.escape(item.get("title", ""))
        link = html.escape(item.get("link", ""))
        summary = html.escape(item.get("summary", ""))
        source = html.escape(item.get("source", ""))
        category = html.escape(item.get("category", ""))
        published = format_relative_time(item.get("published", ""))
        
        tag_style = ""
        border_color = "#e5e7eb" # 默认左侧边框颜色
        if "宏观" in category or "政策" in category:
            tag_style = "background: #fee2e2; color: #991b1b;"
            border_color = "#ef4444"
        elif "国际财经" in category:
            tag_style = "background: #dcfce7; color: #166534;"
            border_color = "#10b981"
        elif "数据" in category:
            tag_style = "background: #f3e8ff; color: #6b21a8;"
            border_color = "#a855f7"
        elif "投资" in category:
            tag_style = "background: #fef3c7; color: #92400e;"
            border_color = "#f59e0b"
        elif "产业" in category or "商业" in category or "科技" in category:
            tag_style = "background: #dbeafe; color: #1e40af;"
            border_color = "#3b82f6"
        else:
            tag_style = "background: #f3f4f6; color: #374151;"

        summary_html = f'<p class="summary">{summary}</p>' if summary else ""
        if summary and len(summary) > 90:
            summary_html += '<button class="more-btn" onclick="toggleSummary(this)">展开全文</button>'
        
        cards.append(f'''
        <article class="card news-card" data-category="{category}" style="border-left: 4px solid {border_color};">
          <div class="meta">
            <span class="tag" style="{tag_style}">{category}</span>
            <span>{source}</span>
            <span class="time-text">{published}</span>
          </div>
          <h2><a href="{link}" target="_blank" rel="noopener noreferrer">{title}</a></h2>
          {summary_html}
        </article>''')

    return filter_html + "\n".join(cards)


def build_report_cards(reports):
    if not reports:
        return '<div class="empty">还没有研报数据。</div>'
    cards = []
    for item in reports:
        title = html.escape(item.get("title", ""))
        link = html.escape(item.get("link", ""))
        detail_raw = item.get("detail") or item.get("link", "")
        if item.get("detail"):
            detail_raw += ("&" if "?" in detail_raw else "?") + "tab=reports"
        detail = html.escape(detail_raw)
        org = html.escape(item.get("org", ""))
        date = html.escape(item.get("date", ""))
        rating = html.escape(item.get("rating", ""))
        stock = html.escape(item.get("stock", ""))
        code = html.escape(item.get("code", ""))
        search_str = f"{stock} {code}".lower()
        rating_color = "#6e6e73"
        if "买入" in rating or "推荐" in rating:
            rating_color = "#dc2626"
        elif "增持" in rating:
            rating_color = "#ea580c"
        elif "中性" in rating or "持有" in rating:
            rating_color = "#2563eb"
        rating_html = f'<span style="color: {rating_color}; font-weight: bold; margin-left: 8px;">[{rating}]</span>' if rating else ""

        badge_bg, badge_fg = "#f3f4f6", "#6e6e73"
        if "买入" in rating or "推荐" in rating:
            badge_bg, badge_fg = "#fee2e2", "#b91c1c"
        elif "增持" in rating:
            badge_bg, badge_fg = "#ffedd5", "#c2410c"
        elif "中性" in rating or "持有" in rating:
            badge_bg, badge_fg = "#dbeafe", "#1d4ed8"
        rating_badge = f'<span class="rating-badge" style="background: {badge_bg}; color: {badge_fg};">{rating}</span>' if rating else ""

        lines = [ln.strip() for ln in (item.get("summary", "") or "").splitlines() if ln.strip()]
        if lines and code and len(lines[0]) <= 30 and code in lines[0]:
            lines.pop(0)
        labels = {"核心观点", "主要观点", "投资要点", "事件", "点评", "摘要", "观点", "投资建议", "核心结论", "报告摘要"}
        while lines and lines[0] in labels:
            lines.pop(0)
        preview = " ".join(lines)
        if len(preview) > 120:
            preview = preview[:120] + "…"
        summary_html = f'<p class="summary clamp2">{html.escape(preview)}</p>' if preview else ""

        cards.append(f'''
        <article class="card report-card" data-search="{search_str}">
          <div class="meta">
            <span class="tag" style="background: #e0e7ff; color: #3730a3;">研报</span>
            <span style="font-weight: bold; color: #1d1d1f;">{stock} ({code})</span>
            <span>{org}</span>
            <span>{date}</span>
            {rating_badge}
          </div>
          <h2><a href="{detail}" rel="noopener noreferrer">{title}</a></h2>
          {summary_html}
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
    categories = {
        "货币": "💵 货币与信用", 
        "物价": "📈 物价与通胀", 
        "工业": "🏭 工业与景气", 
        "外贸": "🏗️ 投资与外贸",
        "大类资产": "💰 大类资产"
    }
    
    cat_nav = ""
    first_cat = True
    for cat_id, cat_name in categories.items():
        active = "active" if first_cat else ""
        cat_nav += f'<button class="sub-tab-btn {active}" onclick="switchSubTab(\'{cat_id}\')" id="subbtn-{cat_id}">{cat_name}</button>'
        first_cat = False

    cat_contents = ""
    first_content = True
    for cat_id in categories.keys():
        display = "block" if first_content else "none"
        first_content = False
        
        cat_charts = [v for k, v in charts.items() if v["category"] == cat_id]
        if cat_id == "货币":
            desired_order = ["货币供应量", "新增人民币贷款", "社会融资规模", "LPR"]
            def sort_key(c):
                for i, name in enumerate(desired_order):
                    if name in c["name"]:
                        return i
                return 99
            cat_charts.sort(key=sort_key)

        charts_html = ""
        if not cat_charts:
            charts_html = '<div class="empty" style="padding: 30px;">该分类暂无数据，可能正在等待接口更新。</div>'
        else:
            for cfg in cat_charts:
                key = [k for k, v in charts.items() if v == cfg][0]
                # 这里改成了紧凑的拼接，避免缩进报错
                charts_html += f'<div class="macro-card" onclick="openChartModal(\'chart-{key}\', \'{cfg["name"]}\')" style="cursor: pointer;"><h3>{cfg["name"]} <span style="font-size:12px; font-weight:normal; color:#98989d; float:right;">点击放大 🔍</span></h3><div style="position: relative; height: 200px; width: 100%;"><canvas id="chart-{key}"></canvas></div></div>'
        
        cat_contents += f'<div id="subtab-{cat_id}" class="sub-tab-content" style="display: {display};">{charts_html}</div>'

    return f'''
    <div class="macro-wrapper">
      <div class="sub-tabs">{cat_nav}</div>
      <div class="sub-tab-container">{cat_contents}</div>
    </div>
    '''

REPORT_PAGE_TEMPLATE = r"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#ffffff">
<title>研报详情</title>
<style>
:root{--ink:#1d1d1f;--sub:#6e6e73;--line:#e5e5ea;--bg:#f5f5f7;--blue:#0071e3}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.75 -apple-system,BlinkMacSystemFont,"PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif;-webkit-font-smoothing:antialiased}
.topbar{position:sticky;top:0;z-index:10;display:flex;align-items:center;padding:11px 14px;background:rgba(255,255,255,.94);-webkit-backdrop-filter:saturate(180%) blur(12px);backdrop-filter:saturate(180%) blur(12px);border-bottom:1px solid var(--line)}
.back{color:var(--blue);text-decoration:none;font-size:15px;white-space:nowrap}
.back:active{opacity:.6}
.topbar .name{flex:1;text-align:center;font-size:14px;color:var(--sub);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;padding:0 8px}
.topbar .gap{width:58px}
main{max-width:760px;margin:0 auto;padding:14px 14px 40px}
.card{background:#fff;border-radius:14px;padding:18px 18px 22px;box-shadow:0 1px 3px rgba(0,0,0,.05)}
.tags{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:12px}
.tag{font-size:12px;line-height:1.6;padding:3px 9px;border-radius:6px;background:#eef2ff;color:#3730a3}
.tag.stock{background:#f2f2f7;color:var(--ink);font-weight:600}
h1{font-size:19px;line-height:1.5;margin:0 0 12px;font-weight:600}
.info{display:flex;flex-wrap:wrap;gap:5px 14px;font-size:13px;color:var(--sub);padding-bottom:14px;border-bottom:1px solid var(--line);margin-bottom:16px}
.body p{margin:0 0 13px;font-size:15.5px;line-height:1.9;color:#2c2c30;text-align:justify;word-break:break-word}
.actions{margin-top:22px;display:flex;flex-direction:column;gap:10px}
.btn{display:block;text-align:center;padding:13px 14px;border-radius:11px;text-decoration:none;font-size:15px;font-weight:600}
.btn.primary{background:var(--blue);color:#fff}
.btn.primary:active{background:#0062c4}
.btn.ghost{background:#f2f2f7;color:var(--ink)}
.note{margin-top:16px;font-size:12px;line-height:1.7;color:#8e8e93}
.empty{background:#fff;border-radius:14px;padding:40px 20px;text-align:center;color:var(--sub)}
.empty a{color:var(--blue);text-decoration:none}
</style>
</head>
<body>
<div class="topbar">
  <a class="back" id="nav-back" href="index.html">&#8592; 返回</a>
  <div class="name" id="bar-title">研报详情</div>
  <div class="gap"></div>
</div>
<main id="app"></main>
<script type="application/json" id="report-data">__DATA__</script>
<script>
(function () {
  var app = document.getElementById('app');
  var bar = document.getElementById('bar-title');

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function ratingColor(r) {
    if (!r) return '#6e6e73';
    if (r.indexOf('买入') >= 0 || r.indexOf('推荐') >= 0) return '#dc2626';
    if (r.indexOf('增持') >= 0) return '#ea580c';
    if (r.indexOf('中性') >= 0 || r.indexOf('持有') >= 0) return '#2563eb';
    return '#6e6e73';
  }

  var list = [];
  try { list = JSON.parse(document.getElementById('report-data').textContent); } catch (e) { list = []; }

  var id = '';
  try { id = new URLSearchParams(location.search).get('id') || ''; } catch (e) { id = ''; }

  // 记住是从哪个标签进来的，返回时回到同一个标签（默认研报）
  var tab = 'reports';
  try { tab = new URLSearchParams(location.search).get('tab') || 'reports'; } catch (e) { tab = 'reports'; }
  if (['news', 'reports', 'sentiment', 'macro'].indexOf(tab) < 0) tab = 'reports';
  var backHref = 'index.html?tab=' + encodeURIComponent(tab);
  var navBack = document.getElementById('nav-back');
  if (navBack) navBack.href = backHref;

  var item = null;
  for (var i = 0; i < list.length; i++) {
    if (list[i].id === id) { item = list[i]; break; }
  }

  if (!item) {
    if (bar) bar.textContent = '研报未找到';
    app.innerHTML = '<div class="empty">没有找到这篇研报的详情。<br><br>' +
      '它可能已经过了保留期，<a href="' + backHref + '">回到列表</a> 看看最新的研报。</div>';
    return;
  }

  if (bar) bar.textContent = (item.stock || '') + (item.code ? ' ' + item.code : '');
  document.title = (item.stock ? item.stock + ' - ' : '') + (item.title || '研报详情');

  var meta = [];
  if (item.org) meta.push('<span>' + esc(item.org) + '</span>');
  if (item.date) meta.push('<span>' + esc(item.date) + '</span>');
  if (item.rating) meta.push('<span class="rating" style="color:' + ratingColor(item.rating) + '">' + esc(item.rating) + '</span>');
  if (item.researcher) meta.push('<span>研究员 ' + esc(item.researcher) + '</span>');
  if (item.industry) meta.push('<span>' + esc(item.industry) + '</span>');
  if (item.pages) meta.push('<span>' + esc(item.pages) + ' 页</span>');

  var paras = String(item.summary || '').split(/\r?\n/).map(function (s) { return s.trim(); }).filter(function (s) { return s.length > 0; });
  // 去掉首行重复的「股票(代码)」
  if (paras.length && paras[0].length <= 30 && item.code && paras[0].indexOf(item.code) >= 0) {
    paras.shift();
  }
  var bodyHtml = paras.length
    ? paras.map(function (p) { return '<p>' + esc(p) + '</p>'; }).join('')
    : '<p style="color:#8e8e93">这篇研报的公开摘要为空，请点下方按钮下载 PDF 查看全文。</p>';

  var pdfBtn = '';
  if (item.pdf) {
    var label = '下载 PDF';
    var bits = [];
    if (item.pages) bits.push(item.pages + ' 页');
    if (item.size) bits.push(item.size + ' KB');
    if (bits.length) label += '（' + bits.join(' / ') + '）';
    pdfBtn = '<a class="btn primary" href="' + esc(item.pdf) + '" target="_blank" rel="noopener noreferrer">' + label + '</a>';
  }

  app.innerHTML =
    '<article class="card">' +
      '<div class="tags"><span class="tag">研报</span>' +
        (item.stock ? '<span class="tag stock">' + esc(item.stock) + (item.code ? ' ' + esc(item.code) : '') + '</span>' : '') +
      '</div>' +
      '<h1>' + esc(item.title) + '</h1>' +
      (meta.length ? '<div class="info">' + meta.join('') + '</div>' : '') +
      '<div class="body">' + bodyHtml + '</div>' +
      '<div class="actions">' + pdfBtn +
        '<a class="btn ghost" href="' + backHref + '">回到研报列表</a>' +
      '</div>' +
      '<div class="note">摘要来自东方财富公开研报页面，仅供个人研究参考，不构成投资建议。</div>' +
    '</article>';
})();
</script>
</body>
</html>
"""


def build_report_page(reports):
    """生成单篇研报详情页（数据内嵌，无需额外请求）"""
    payload = []
    for item in reports:
        payload.append({
            "id": item.get("infoCode") or item.get("id") or "",
            "title": item.get("title", ""),
            "stock": item.get("stock", ""),
            "code": item.get("code", ""),
            "org": item.get("org", ""),
            "date": item.get("date", ""),
            "rating": item.get("rating", ""),
            "researcher": item.get("researcher", ""),
            "industry": item.get("industry", ""),
            "pages": item.get("pages", ""),
            "size": item.get("size", ""),
            "pdf": item.get("pdf", ""),
            "summary": item.get("summary", ""),
        })
    data_json = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    return REPORT_PAGE_TEMPLATE.replace("__DATA__", data_json)


def main():
    news_data = load_json(NEWS_FILE, {"updated": "", "count": 0, "items": []})
    reports_data = load_json(REPORTS_FILE, [])
    sentiment_data = load_json(SENTIMENT_FILE, {})
    macro_data = load_json(MACRO_FILE, {"charts": {}})

    news_items = news_data.get("items", [])
    news_updated = html.escape(format_relative_time(news_data.get("updated", "")))
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
<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
<meta http-equiv="Pragma" content="no-cache">
<meta http-equiv="Expires" content="0">
<title>个人财经终端</title>
<meta property="og:title" content="个人财经终端">
<meta property="og:description" content="每日新闻、券商研报、市场情绪与宏观数据的聚合看板">
<meta property="og:type" content="website">
<link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>📈</text></svg>">
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

/* 新闻分类筛选栏 */
.filter-bar {{ display: flex; gap: 8px; overflow-x: auto; padding-bottom: 12px; margin-bottom: 4px; }}
.filter-btn {{ background: #fff; border: 1px solid #e5e7eb; padding: 6px 14px; border-radius: 20px; font-size: 13px; color: #3a3a3c; cursor: pointer; white-space: nowrap; transition: all 0.2s; }}
.filter-btn.active {{ background: #1d1d1f; color: #fff; border-color: #1d1d1f; }}

/* 搜索框样式 */
.search-container {{ margin-bottom: 16px; }}
.search-input {{ width: 100%; padding: 12px 16px; border-radius: 10px; border: 1px solid #e5e7eb; font-size: 14px; background: #fff; color: #1d1d1f; outline: none; transition: border-color 0.2s; }}
.search-input:focus {{ border-color: #3b82f6; }}

.sentiment-dashboard {{ background: transparent; }}
.sentiment-time {{ text-align: center; font-size: 12px; color: #98989d; margin-bottom: 20px; }}

.macro-wrapper {{ background: transparent; }}
.sub-tabs {{ display: flex; gap: 10px; overflow-x: auto; margin-bottom: 16px; padding-bottom: 4px; }}
.sub-tab-btn {{ background: rgba(0,0,0,0.05); border: none; padding: 8px 16px; border-radius: 20px; font-size: 13px; font-weight: 500; color: #3a3a3c; cursor: pointer; white-space: nowrap; }}
.sub-tab-btn.active {{ background: #1d1d1f; color: #fff; }}
.macro-card {{ background: #fff; border-radius: 14px; padding: 16px; box-shadow: 0 1px 2px rgba(0, 0, 0, .04); margin-bottom: 16px; }}
.macro-card h3 {{ font-size: 14px; margin: 0 0 16px 0; color: #3a3a3c; }}

/* 返回顶部悬浮按钮 */
.back-to-top {{ position: fixed; bottom: 30px; right: 20px; width: 44px; height: 44px; background: #1d1d1f; color: #fff; border-radius: 50%; display: none; align-items: center; justify-content: center; box-shadow: 0 4px 12px rgba(0,0,0,0.15); cursor: pointer; z-index: 999; border: none; font-size: 20px; }}

@media (prefers-color-scheme: dark) {{
  body {{ background: #000; color: #f5f5f7; }}
  header {{ background: rgba(0, 0, 0, .8); border-bottom-color: rgba(255, 255, 255, .12); }}
  .sub, .meta {{ color: #98989d; }}
  .card, .empty, .macro-card, .search-input, .filter-btn {{ background: #1c1c1e; box-shadow: none; border-color: #3a3a3c; color: #f5f5f7; }}
  .summary {{ color: #d1d1d6; }}
  .macro-card h3 {{ color: #f5f5f7; }}
  .tab-btn {{ color: #98989d; }}
  .tab-btn.active {{ color: #f5f5f7; border-bottom-color: #f5f5f7; }}
  .filter-btn.active {{ background: #f5f5f7; color: #000; border-color: #f5f5f7; }}
  .sub-tab-btn {{ background: rgba(255,255,255,0.1); color: #d1d1d6; }}
  .sub-tab-btn.active {{ background: #f5f5f7; color: #000; }}
  .meta span[style*="color: #1d1d1f;"] {{ color: #f5f5f7 !important; }}
  .sentiment-dashboard div[style*="background: #fff;"] {{ background: #1c1c1e !important; }}
  .sentiment-dashboard div[style*="border-left: 4px solid #1d1d1f;"] {{ border-left-color: #f5f5f7 !important; }}
  .sentiment-dashboard div[style*="color: #1d1d1f;"] {{ color: #f5f5f7 !important; }}
  .back-to-top {{ background: #f5f5f7; color: #000; }}
}}
/* 图表放大弹窗样式 */
.chart-modal-content {{ position: fixed; top: 10vh; left: 2vw; width: 96vw; height: 80vh; background: #fff; border-radius: 16px; z-index: 1001; display: none; flex-direction: column; box-shadow: 0 10px 30px rgba(0,0,0,0.2); transform: scale(0.95); opacity: 0; transition: all 0.3s; }}
.chart-modal-content.show {{ display: flex; transform: scale(1); opacity: 1; }}
.chart-modal-body {{ padding: 10px; flex: 1; position: relative; min-height: 0; }}
@media (prefers-color-scheme: dark) {{ .chart-modal-content {{ background: #1c1c1e; }} }}

/* ==== UI 轻量优化 ==== */
.summary {{ display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }}
.summary.clamp2 {{ -webkit-line-clamp: 2; }}
.summary {{ font-size: 15px; line-height: 1.72; }}
.summary.expanded {{ -webkit-line-clamp: unset; overflow: visible; }}
.more-btn {{ background: none; border: none; padding: 4px 0 0; font-size: 13px; color: #0071e3; cursor: pointer; }}
.rating-badge {{ margin-left: auto; font-size: 12px; font-weight: 600; padding: 2px 10px; border-radius: 999px; white-space: nowrap; }}
.report-card .summary {{ font-size: 13.5px; color: #6e6e73; margin-top: 8px; }}

.date-group {{ display: flex; align-items: center; gap: 10px; margin: 14px 2px 10px; font-size: 12px; font-weight: 600; color: #6e6e73; }}
.date-group::after {{ content: ""; flex: 1; height: 1px; background: rgba(0,0,0,.08); }}
#to-top {{ position: fixed; right: 16px; bottom: 28px; width: 42px; height: 42px; border-radius: 50%; border: none; background: rgba(29,29,31,.82); color: #fff; font-size: 18px; line-height: 42px; text-align: center; cursor: pointer; display: none; z-index: 200; box-shadow: 0 2px 8px rgba(0,0,0,.2); }}
.search-wrap {{ position: relative; }}
.search-clear {{ position: absolute; right: 10px; top: 50%; transform: translateY(-50%); width: 22px; height: 22px; border: none; border-radius: 50%; background: #e5e7eb; color: #6e6e73; font-size: 13px; line-height: 22px; cursor: pointer; padding: 0; }}
.search-count {{ font-size: 12px; color: #6e6e73; margin-top: 8px; min-height: 16px; }}
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
<button id="to-top" title="回到顶部">↑</button>
<main>
  <div id="tab-news">{news_cards_html}</div>
  
  <div id="tab-reports" style="display: none;">
    <div class="search-container">
      <div class="search-wrap">
        <input type="text" id="report-search" class="search-input" placeholder="🔍 输入股票代码或名称搜索研报..." oninput="filterReports()">
        <button class="search-clear" id="search-clear" onclick="clearSearch()" style="display:none;">×</button>
      </div>
      <div class="search-count" id="search-count"></div>
    </div>
    <div id="report-list">
      {reports_cards_html}
    </div>
    <div id="report-empty" class="empty" style="display: none;">未找到相关研报</div>
  </div>

  <div id="tab-sentiment" style="display: none;">{sentiment_cards_html}</div>
  <div id="tab-macro" style="display: none;">{macro_cards_html}</div>
</main>

<!-- 图表放大弹窗 -->
<div class="modal-overlay" id="chart-modal-overlay" onclick="closeChartModal()"></div>
<div class="chart-modal-content" id="chart-modal-content">
  <div class="modal-header">
    <h2 id="chart-modal-title">图表放大</h2>
    <button class="close-btn" onclick="closeChartModal()">✕</button>
  </div>
  <div class="chart-modal-body">
    <canvas id="chart-modal-canvas"></canvas>
  </div>
</div>

<button class="back-to-top" id="backToTop" onclick="scrollToTop()">↑</button>

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
  window.scrollTo(0, 0);
  if(tab === 'macro') lazyRenderCharts();
}}

function initBackToTop() {{
  var btn = document.getElementById('to-top');
  if (!btn) return;
  btn.onclick = function () {{ window.scrollTo(0, 0); }};
  window.addEventListener('scroll', function () {{
    btn.style.display = window.scrollY > 400 ? 'block' : 'none';
  }}, {{ passive: true }});
}}


// 打开页面时恢复标签：支持 index.html?tab=reports 或 #reports
(function(){{
  var t = '';
  try {{ t = new URLSearchParams(location.search).get('tab') || ''; }} catch(e) {{ t = ''; }}
  if (!t && location.hash) {{ t = location.hash.replace(/^#/, ''); }}
  if (['news','reports','sentiment','macro'].indexOf(t) >= 0) {{ switchTab(t); }}
  initBackToTop();
}})();

function toggleSummary(btn) {{
  var p = btn.previousElementSibling;
  if (!p) return;
  var on = p.classList.toggle('expanded');
  btn.textContent = on ? '收起' : '展开全文';
}}

// 新闻分类筛选
function filterNews(category, btn) {{
  // 更新按钮状态
  const buttons = document.querySelectorAll('.filter-btn');
  buttons.forEach(b => b.classList.remove('active'));
  btn.classList.add('active');

  // 过滤卡片
  document.querySelectorAll('.date-group').forEach(g => {{
    g.style.display = category === 'all' ? 'flex' : 'none';
  }});

  const cards = document.querySelectorAll('.news-card');
  cards.forEach(card => {{
    if (category === 'all' || card.getAttribute('data-category') === category) {{
      card.style.display = 'block';
    }} else {{
      card.style.display = 'none';
    }}
  }});
}}

// 研报搜索
function filterReports() {{
  const query = document.getElementById('report-search').value.toLowerCase().trim();
  const cards = document.querySelectorAll('.report-card');
  let visibleCount = 0;

  cards.forEach(card => {{
    const searchData = card.getAttribute('data-search');
    if (searchData.includes(query)) {{
      card.style.display = 'block';
      visibleCount++;
    }} else {{
      card.style.display = 'none';
    }}
  }});

  const emptyMsg = document.getElementById('report-empty');
  emptyMsg.style.display = visibleCount === 0 ? 'block' : 'none';

  const clearBtn = document.getElementById('search-clear');
  if (clearBtn) clearBtn.style.display = query ? 'block' : 'none';
  const countEl = document.getElementById('search-count');
  if (countEl) countEl.textContent = query ? ('匹配到 ' + visibleCount + ' 条研报') : '';

  // 分组标签在筛选时隐藏
  document.querySelectorAll('.date-group').forEach(function (g) {{
    g.style.display = query ? 'none' : 'flex';
  }});
}}

function clearSearch() {{
  const input = document.getElementById('report-search');
  input.value = '';
  filterReports();
}}

function switchSubTab(catId) {{
  document.querySelectorAll('.sub-tab-content').forEach(el => el.style.display = 'none');
  document.querySelectorAll('.sub-tab-btn').forEach(el => el.classList.remove('active'));
  document.getElementById('subtab-' + catId).style.display = 'block';
  document.getElementById('subbtn-' + catId).classList.add('active');
  lazyRenderCharts();
}}

// 返回顶部逻辑
window.onscroll = function() {{
  const btn = document.getElementById('backToTop');
  if (document.body.scrollTop > 300 || document.documentElement.scrollTop > 300) {{
    btn.style.display = 'flex';
  }} else {{
    btn.style.display = 'none';
  }}
}};

function scrollToTop() {{
  window.scrollTo({{ top: 0, behavior: 'smooth' }});
}}

function lazyRenderCharts() {{
  const isDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  const textColor = isDark ? '#98989d' : '#6e6e73';
  const gridColor = isDark ? '#3a3a3c' : '#e5e7eb';

  const activeContent = document.querySelector('.sub-tab-content[style*="display: block"]');
  if (!activeContent) return;

  activeContent.querySelectorAll('canvas').forEach(canvas => {{
    const chartId = canvas.id.replace('chart-', '');
    if (chartInstances[chartId]) return;

    const cfg = macroData[chartId];
    if (!cfg) return;

    let datasets = [];
    let chartType = cfg.type === 'multi_line' ? 'line' : cfg.type;

    if (cfg.type === 'mixed') {{
      chartType = 'bar';
      datasets.push({{ type: 'bar', label: '两融余额', data: cfg.bar_data, backgroundColor: cfg.bar_color + '80', borderRadius: 4, yAxisID: 'y' }});
      datasets.push({{ type: 'line', label: '融资余额', data: cfg.line_data, borderColor: cfg.line_color, borderWidth: 2, tension: 0.3, pointRadius: 2, fill: false, yAxisID: 'y1' }});
    }} else if (cfg.type === 'multi_line') {{
      datasets = cfg.series.map(s => ({{ label: s.name, data: s.data, borderColor: s.color, backgroundColor: s.color + '20', borderWidth: 2, tension: 0.3, pointRadius: 2, fill: false }}));
    }} else if (cfg.type === 'bar') {{
      const bgColors = cfg.data.map(v => v >= 0 ? cfg.color : '#10b981');
      datasets = [{{ data: cfg.data, backgroundColor: bgColors, borderRadius: 4 }}];
    }} else {{
      datasets = [{{ data: cfg.data, borderColor: cfg.color, backgroundColor: cfg.color + '20', borderWidth: 2, tension: 0.3, pointRadius: 3, fill: true }}];
    }}

    const config = {{
      type: chartType,
      data: {{ labels: cfg.labels, datasets: datasets }},
      options: {{
        responsive: true, maintainAspectRatio: false,
        plugins: {{ 
          legend: {{ display: cfg.type === 'multi_line' || cfg.type === 'mixed', position: 'top', labels: {{ boxWidth: 12, font: {{ size: 10 }} }} }},
          tooltip: {{ mode: 'index', intersect: false }}
        }},
        scales: {{
          x: {{ 
            grid: {{ display: false }}, 
            ticks: {{ 
              color: textColor, 
              maxRotation: 60, 
              minRotation: 45, 
              font: {{ size: 10 }},
              autoSkip: true,
              maxTicksLimit: 12,
              callback: function(value) {{
                const str = this.getLabelForValue(value);
                // 匹配 2021年11月、2021-11、202111 等格式
                const match = str.match(/(\d{4})\D*(\d{1,2})/);
                if (match) {{
                  const year = match[1].slice(2); // 取后两位年
                  const month = match[2].padStart(2, '0'); // 补齐两位月
                  return year + '-' + month;
                }}
                return str;
              }}
            }} 
          }},
          y: {{ grid: {{ color: gridColor, drawBorder: false }}, ticks: {{ color: textColor, font: {{ size: 10 }} }} }}
        }}
      }}
    }};

    if (cfg.baseline) {{
      config.options.plugins.annotation = {{
        annotations: {{ line1: {{ type: 'line', yMin: cfg.baseline, yMax: cfg.baseline, borderColor: '#ef4444', borderWidth: 1, borderDash: [5, 5], label: {{ display: true, content: '枯荣线', position: 'end' }} }} }}
      }};
    }}

    chartInstances[chartId] = new Chart(canvas.getContext('2d'), config);
  }});
}}

document.addEventListener('DOMContentLoaded', () => {{
  setTimeout(lazyRenderCharts, 500);
}});
let modalChartInstance = null;

function openChartModal(chartId, title) {{
  document.getElementById('chart-modal-overlay').classList.add('show');
  document.getElementById('chart-modal-content').classList.add('show');
  document.getElementById('chart-modal-title').innerText = title;
  document.body.style.overflow = 'hidden';

  const originalCfg = macroData[chartId.replace('chart-', '')];
  if (!originalCfg) return;

  if (modalChartInstance) {{
    modalChartInstance.destroy();
  }}

  const canvas = document.getElementById('chart-modal-canvas');
  const isDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  const textColor = isDark ? '#98989d' : '#6e6e73';
  const gridColor = isDark ? '#3a3a3c' : '#e5e7eb';

  let datasets = [];
  let chartType = originalCfg.type === 'multi_line' ? 'line' : originalCfg.type;

  if (originalCfg.type === 'mixed') {{
    chartType = 'bar';
    datasets.push({{ type: 'bar', label: '两融余额', data: originalCfg.bar_data, backgroundColor: originalCfg.bar_color + '80', borderRadius: 4, yAxisID: 'y' }});
    datasets.push({{ type: 'line', label: '融资余额', data: originalCfg.line_data, borderColor: originalCfg.line_color, borderWidth: 2, tension: 0.3, pointRadius: 2, fill: false, yAxisID: 'y1' }});
  }} else if (originalCfg.type === 'multi_line') {{
    datasets = originalCfg.series.map(s => ({{ label: s.name, data: s.data, borderColor: s.color, backgroundColor: s.color + '20', borderWidth: 2, tension: 0.3, pointRadius: 2, fill: false }}));
  }} else if (originalCfg.type === 'bar') {{
    const bgColors = originalCfg.data.map(v => v >= 0 ? originalCfg.color : '#10b981');
    datasets = [{{ data: originalCfg.data, backgroundColor: bgColors, borderRadius: 4 }}];
  }} else {{
    datasets = [{{ data: originalCfg.data, borderColor: originalCfg.color, backgroundColor: originalCfg.color + '20', borderWidth: 2, tension: 0.3, pointRadius: 3, fill: true }}];
  }}

  const config = {{
    type: chartType,
    data: {{ labels: originalCfg.labels, datasets: datasets }},
    options: {{
      responsive: true, maintainAspectRatio: false,
      plugins: {{ 
        legend: {{ display: originalCfg.type === 'multi_line' || originalCfg.type === 'mixed', position: 'top', labels: {{ boxWidth: 12, font: {{ size: 12 }} }} }},
        tooltip: {{ mode: 'index', intersect: false }}
      }},
      scales: {{
        x: {{ 
          grid: {{ display: false }}, 
          ticks: {{ 
            color: textColor, 
            maxRotation: 90, 
            minRotation: 45, 
            font: {{ size: 11 }}, 
            autoSkip: true, 
            maxTicksLimit: 24,
            callback: function(value) {{
              const str = this.getLabelForValue(value);
              const match = str.match(/(\d{4})\D*(\d{1,2})/);
              if (match) {{
                const year = match[1].slice(2);
                const month = match[2].padStart(2, '0');
                return year + '-' + month;
              }}
              return str;
            }}
          }} 
        }},
        y: {{ grid: {{ color: gridColor, drawBorder: false }}, ticks: {{ color: textColor, font: {{ size: 11 }} }} }},
        y1: {{ display: false, grid: {{ display: false }} }}
      }}
    }}
  }};

  if (originalCfg.baseline) {{
    config.options.plugins.annotation = {{
      annotations: {{
        line1: {{ type: 'line', yMin: originalCfg.baseline, yMax: originalCfg.baseline, borderColor: '#ef4444', borderWidth: 1, borderDash: [5, 5], label: {{ display: true, content: '枯荣线', position: 'end' }} }}
      }}
    }};
  }}

  modalChartInstance = new Chart(canvas.getContext('2d'), config);
}}

function closeChartModal() {{
  document.getElementById('chart-modal-overlay').classList.remove('show');
  document.getElementById('chart-modal-content').classList.remove('show');
  document.body.style.overflow = '';
  if (modalChartInstance) {{
    modalChartInstance.destroy();
    modalChartInstance = null;
  }}
}}
</script>
</body>
</html>'''

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html_doc)

    report_path = os.path.join(os.path.dirname(OUTPUT_FILE), "report.html")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(build_report_page(reports_data))

    print(f"已生成 {OUTPUT_FILE}，前端交互已全面优化。")
    print(f"已生成 {report_path}，共 {len(reports_data)} 篇研报详情。")


if __name__ == "__main__":
    main()

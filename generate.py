import json
import os
import base64
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


REPORT_TYPE_ORDER = ["个股研报", "行业研报", "产业分析"]


def report_type(item):
    """判断研报类型：优先用数据里的 reportType，否则按字段推断"""
    rt = (item.get("reportType") or "").strip()
    if rt:
        return rt
    if not item.get("stock") and item.get("industry"):
        return "行业研报"
    return "个股研报"


def build_report_filter(reports):
    """研报分类胶囊：全部 / 个股研报 / 行业研报（将来会有产业分析）"""
    present = []
    for item in reports:
        t = report_type(item)
        if t and t not in present:
            present.append(t)
    present.sort(key=lambda x: REPORT_TYPE_ORDER.index(x) if x in REPORT_TYPE_ORDER else 99)
    if len(present) < 2:
        return ""

    html_parts = ['<div class="filter-bar" id="report-type-bar">']
    html_parts.append('<button class="filter-btn active" onclick="filterReportType(\'all\', this)">全部</button>')
    for t in present:
        html_parts.append(f'<button class="filter-btn" onclick="filterReportType(\'{html.escape(t)}\', this)">{html.escape(t)}</button>')
    html_parts.append('</div>')
    return "".join(html_parts)


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
        industry = html.escape(item.get("industry", ""))
        # 行业研报没有股票名、只有行业名；个股研报两者都有
        is_industry = (not stock) and bool(industry)
        search_str = f"{stock} {code} {industry}".lower()
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

        # 行业研报：标签换成绿色「行业研报」，主体位置显示行业名
        rtype = report_type(item)
        if is_industry:
            tag_bg, tag_fg, tag_text = "#ecfdf5", "#047857", rtype
            subject = industry
        else:
            tag_bg, tag_fg, tag_text = "#e0e7ff", "#3730a3", rtype
            subject = f"{stock} ({code})" if code else stock

        cards.append(f'''
        <article class="card report-card" data-search="{search_str}" data-type="{html.escape(rtype)}">
          <div class="meta">
            <span class="tag" style="background: {tag_bg}; color: {tag_fg};">{tag_text}</span>
            <span style="font-weight: bold; color: #1d1d1f;">{subject}</span>
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

ICON_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAALQAAAC0CAYAAAA9zQYyAAAO40lEQVR4nOzdC3Bc1X0G8O/cu3pY"
    "RhI2tiWvVpKN8YOHQ5syxQGneKaTlDbEUZMmQ2lpOzwmNJPJZNKBgTTMtM1kxtBOA51Mpw1tPU3b"
    "JA7tAHFJ25k0PIIJIQkEsPED21jah2RZkZFkyZZ27z35n7Vly7Iee3fv7t579/vN7Ozq7l4B3s+H"
    "c/7nnnNjqKLly5e3LF26dIvrIq6UapdDq5XCanlu1/rssxy/DBQYWutT8jQg31O/PPfL9zRw7rnf"
    "snT/+Pj4K8PDw6OoEoUKSyQSV2lt3SZB/aj8oXxQDtWBoiQroX9RnncD7rOpVOowKqgSgbYlxB9U"
    "yv6o/C2WIGMDqGbId35IHruVcnZLuF+SQw7KqJyBtjo6uu6UlvgvJcTdIAKOSev9cCrV90157aIM"
    "yhLoeLxzu22rr8ivvw5Es0io39JaPZRO9z4Ln/kaaOla3Cg9jMekRd4CokXpPY6jHshkel+GT3wJ"
    "dHt71zWxGB6R7sVtIPJMywBSfzGZTO5FiUoO9Nl+MnZKmG0QFUm6IY5S+l4J9U6UoJQQqo6Ozi9b"
    "lvVVCbMFohKczZD6WEtLqzU6OvICilRsC12XSHR/W1rmj4PId/rJZLLvD+XFFDzyHOiOjo4rLMt+"
    "Wk7dCqIykdr1C66b/b1MJjPk5TxPgW5r615bX6+/L6ddCaKy00cmJ/HhwcG+o4WeUXDfd8WKFc11"
    "dfhfhpkqR62rr1ffM9f8FHpGoYFWjY1NT3LamipNMrexqan52yiwN1FQlSOR6Noho9A/BlEVSKjX"
    "S/WjUaof31/ss4sGWqoZd0uYHwVRFUkGtzY3t+4fGxvZt+DnFnozHu++ybbxPHiJJwWATL6cdl18"
    "KJPp2zPfZ+YNtJTnEkrFXpPmfiWIAkLKeSe0zr0/nU6n5np/3kGh1Jq/xjBT0JhMmmzO+/5cB+Px"
    "rpttW70EooDS2rk+lUq9Ofv4nC20ZZlrmYmCzJqzUHFJoBOJxDZp1m8BUYBJ1eO3TFZnH7cu/aD1"
    "ZRCFgv0Xs49cFOjOzs4eXnREYWF6EtJK3zrz2EWB1lr9FYhCxd4x86fzgZa6869Iv2QziEJEWunr"
    "4/H4pumfrQtv2LeCKIQsK9Zz/vWFw6oHRKF0Ibv5iZWVK9e0NzS4GelyVHxrMKJSaXHmjOoYGurt"
    "z7fQ9fVOD8NMYWWyKw3yx8xr69wBdjco1KYzrMzSqiVLlpqFiPUgCq+p8fGxlbGGhoZrwTBT+NUv"
    "WbLkmphlWe0gigCTZct11RoQRYDJckxqG2yhKRJMlhloigyTZUtrtQZEEWCyHJNnttAUFexyUHTk"
    "+9Dy3AqiaGjlRuUUKQw0RQoDTZHCQFOkMNAUKQw0RQoDTZESA9Ec1KYWYG0zcMaB3vceMHgGYcBA"
    "00XUh+KwfrcL1vKGi467B96D+40j0EdPIchUZ2e3BlF7I+zPbIK1Yf6JYz2eRe4rbwIBDjX70AT1"
    "8S7UPXbjgmHOf25pHezPXo0gY5ejll3VDPu+jbASSws+xYo3wZHzcHgMQcRA1yDdaMO+Yy3sD3eg"
    "GKp7KTQDTUGgfnUZ7Hs3XjLo8yQb3GEXA10rWupg3b0e9o0+3Adq8DSCioGuAeo326WLcWV+UFcq"
    "NzUOfWAUQcVAR5kpxZlB36bL4RfnX95BkDHQEWVKcbFPrYVfTA3aeXQvcDC4rbPBQEdNEaW4xTg/"
    "PgH3n6VlHs0i6BjoiCi1FDcXd3gS7hMHoV8/ibBgoCPAl1LcLM7/peF8612oMw7ChIEOMz9LceeY"
    "Kob79wfyFyGFcQd8Bjqk1JYV0ipv8KUUNy236yj0U0mEGQMdRutbEPv8tfCLe2gEjrTKGAjHNc8L"
    "YaBDyP70BvhBT0gp7t+kVX5uAFHBQIeMuq3Dl5JcmEpxXjDQIaKvaCh5siSMpTgvGOgQif3ROqh6"
    "G8UKaynOCwY6LK5fDqvI8lzYS3FeMNBhUGfBvusqFCO3610pxfWhVjDQIWD1dMFqW+LpnCiV4rxg"
    "oIPOXAL6iW5PpzgvDkgX4yBqEVd9B5x9j7eas3sqJ7XlI6hVbKEDTN20EtZ1yzyd437zCNRYDrWK"
    "LXRAmctBrTu9DQT1kVHoH0Rn1q8YbKEDyv7UGljLvN2CPfcPtdlvnomBDqLOJti/k/B0ivO9FJCc"
    "QK1jlyOAYvdt9PR59+QUnO8cA7GFDhyz5YBa1+LpHPcbhyM9ne0FW+gA0c0xWL+/ztM57t6T0D86"
    "ATqLLXSA2H9wJazLvH0lztc5EJyJgQ6KDc2wt632dIrzX8eAwUnQBQx0QNif9jYQ1ENn4D7ZC7oY"
    "Ax0A+VUoHd5WoeSeCPaWXNXCQWGVmVUotsdVKGb5FN4YBl2KLXSVeV2FoqccuDsPg+bGQFdTEatQ"
    "nF3HgPemQHNjoKsodu96T5930+PQz6ZA82Ogq8T65BqoFY2eznH+kTXnxTDQs6hfWw6sbgKmXODE"
    "abj7R/2fVi5iFYr7fD9wKJg36gkSBvoctflyWPdsmHPtnqkq6BcGoF/zp7JQzCqU3H8cjfyKbT8w"
    "0EJ9JIHYnfNfQ5Hf3VMeemQK7suD0D88XvQtgrkKpbxqPtDWn26EfUt7QZ9VrfWwfzsByCM/QPvh"
    "IBwJt/pFYdPP+U3JuQqlrGr3Xt9NEq4vXOu5tZyL+/ZJuC8Own3lxIL9bUtqzl4v3M/e/xNeuO9B"
    "bbbQq2R27sH35W/z6wfrmmX5h75rPdyfDkG/dPzS/jZXoVREzQVabWyBff91UJf5t1H4+d9db8G+"
    "aRUgj9n97WJXoXAg6E1NdTnUb6xC7DNXo9L08CSUx/uf5B7bB/3KEMibmmmhrdvXwO7xVvv1i9cw"
    "u2+dZJiLFP1Am40OP7up6J07q8F5gjOCxYp2oFvrEHvgOs+LTquJq1BKE91Ady1F7MHNnv93X03u"
    "gEy1Px3uu1BVWyQDrd6/HPbnroZqLP4/zz0yBr33JKwtK6E8bmVbLGfnO1J4dkHFi1ygLZnGtu/0"
    "thXAbObaDedr+6GyGu633s3fP9va2iaPVWUp903/M/FGNO97UkmRKtt5mcaeT+6pXmhzEf08TOuv"
    "TLhvWJGvO/vBrELJfe5VXrjvg2i00D5NY+f+7m3olxfetMXMAJqHY3YHle6IJbVtM0tYCq5C8U/4"
    "W+i2xrODv9XFT2PrU1nkHn2r+OuNr2iQYLdJy73K8+pt99gYnAdfA/kj1IH2YxrbzUzA2fGmf6Wy"
    "Ky/Lh9v6wKr81XkLMXtr5B6WMJ+M1s0vqym0gfZjGtvsC+f87T5gojwbHS7U3zbXeuQefl3+ItXW"
    "TX3KLZSBtu5YC3t7F0rh/H8GboU2a8nvxr95GZTUxrWU5fQ7o8DhMZboyiBcgfZpGtvcVMfl6ulI"
    "Ck+VQ6ax7Qc2w1rXjGLpSQfO42/7tjaQgiccgfZhGttcwpnbIZWMvnFQdAU/0O9bhtgXriltGvuo"
    "lMYekTCPsJoQdcEOdLwJsT+7Fqqh8L3fZnPz09gHOACrEYEOdOyB0sLsyDS2u8A0NkVPcAMtExSq"
    "vfjZv0KmsSl6AhtotbEVxTC7DLl//Rb0wVFQ7QluCz3hfacg36exKXSCG+iT3q4+K/c0NoVDYAOt"
    "949AHz9d0GqRSk5jU7AF9x4rUmbLmVm9UwvXjnP/ephhpvOCfy3HsjpY922Cff3yiw6bBaXO1w8B"
    "b78HomnhuThpVSPUr18BpRV0/wSvx6A51e7uoxRJvE8hRQoDTZHCQFOkMNAUKQw0RUpolmC1tbWh"
    "s7MTTU3+3EaCCjMxMYF0Oo3+/n6EQSgCvW3bLdi6dSuoevbs2YPnnnseQRf4Lsfq1asZ5gC4+eab"
    "0dVV2tYRlRD4QJtuBgVDe3tpG2FWAgeFFCmB70OHZTBSC8LwXQS+hU4mkzh06BCousx3YL6LoAvN"
    "xUnxeDz/YNmuskzZ7vjx46EIs8Gr7ShSOCikSDGBHgFRNIxYWmMARBFgsmxaaAaaomLAUkoz0BQJ"
    "JsvsclBkmCybmUIGmqLCtNDsclA0mCzH2IemqJAsH7POnLHfkGRztpDCbkrst4aGevsl26+CKMSk"
    "TX5ucHDw+Lmpb/00iEJMAp3PcD7QrptjoCm0TJc5m518yrzOBzqTyRyQXvRBEIWSetV0N8yrGVfb"
    "sdtBYXUhu+cDrbXDQFMozewyq5lvdHZ2peVQHEQhYbrKqVTvpumfrYvfdO8GUag4n5/5k5r9diLR"
    "/bxSuAVEASet8wvSOm+beeySJViuq/8cRCEggX5o9rFLAp3J9O2Rjz4DokDTz6TTvT+afXSeRbL6"
    "S1Kr5h0sKZBMNrNZzNmTmDPQyWRyr/Sj/x1EASTZ/KeBgb59c7037zYG2ezU/dJH6QNRgEjrnHSc"
    "3Jfme3/eQA8MDJxwXfTIL5gAUQBIFk9Lb2N7JpMZmu8zC240k8n0vq6UvgdEASA9hj9Jp9M/X+gz"
    "NhYxOjq6t6WldYlSiruOU9VI6/xIOt33+GKfUyiMSiS6dkuoPwKiCpOW+X9kAsVkb9GVVYXubacn"
    "Jk7dIb/4AIgqyFyrMTExdjsKCLNR8GaNw8PDo66b7QH3wqPKGdE6t91kr9ATPO0+KqPLg6dPj3dy"
    "JpHKTfrM/22yJoNAT7vdLzoonG1iYmJqdHRklwwUGzlQpHLQ2v2bVCp5l2RtEh4VOiicUyLRfYfM"
    "2uyUl/UgKtHZOrMpzfV9B0UqKdBGR0f3ByxL/ycXBlBpdL+0zLemUqk3UQLPXY7ZxsZGUpdf3rrT"
    "dVVMWusb/PidVFOm5PG4ZOf2ZDLZixKV3ELP1N7eviYWa/iq/Mv1gGgBZusBGYPtymYnHxoYGDgG"
    "n/ga6GnxePdNtq1lVkfdAKJL6J/mcrivv7/vZ/BZWQI9/bs7Oro+aVlqh7xeCyLgXcD9onQtdqHA"
    "iRKvyhnoaXY83iUDR2yXf9x26Y5sBNUMqVpIHdn9rnzv35UgvyyHyrpwpBKBvkgikbhK5nM+IS8l"
    "4Ngi/SjeWi5Czq50Ui9JgHfLy2ekanEYFVTxQM9SLwHvkj8EmX20O6V7cu616lRKd5ln+UwLKEhk"
    "GlonZUjXZ56lQUq6rk5Kw9tnXkuAzaKQKVTJLwEAAP//cL7jggAAAAZJREFUAwCGFi/yJ1T2FgAA"
    "AABJRU5ErkJggg=="
)


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

  if (bar) {{
    var _subj = item.stock || item.industry || '';
    bar.textContent = _subj + ((item.stock && item.code) ? ' ' + item.code : '');
  }}
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
    pdfBtn = '<a class="btn primary" href="' + esc(item.pdf) + '" target="_blank" rel="noopener noreferrer" referrerpolicy="no-referrer">' + label + '</a>';
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
    report_filter_html = build_report_filter(reports_data)
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
<link rel="icon" type="image/png" sizes="180x180" href="icon.png">
<link rel="shortcut icon" type="image/png" href="icon.png">
<link rel="apple-touch-icon" href="icon.png">
<meta property="og:image" content="icon.png">
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
#to-top {{ position: fixed; right: 16px; bottom: 28px; width: 42px; height: 42px; border-radius: 50%; border: none; background: rgba(29,29,31,.82); color: #fff; font-size: 18px; line-height: 42px; text-align: center; cursor: pointer; display: none; z-index: 200;  }}
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
        <input type="text" id="report-search" class="search-input" placeholder="🔍 输入股票/行业/标题关键词搜索研报..." oninput="filterReports()">
        <button class="search-clear" id="search-clear" onclick="clearSearch()" style="display:none;">×</button>
      </div>
      <div class="search-count" id="search-count"></div>
    </div>
    {report_filter_html}
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
  // 更新按钮状态（限定在新闻胶囊条内，避免影响研报胶囊）
  const buttons = document.querySelectorAll('#filter-bar .filter-btn');
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

// 研报搜索 + 类型筛选
var activeReportType = 'all';

function filterReports() {{
  const query = document.getElementById('report-search').value.toLowerCase().trim();
  const cards = document.querySelectorAll('.report-card');
  let visibleCount = 0;

  cards.forEach(card => {{
    const searchData = card.getAttribute('data-search') || '';
    const typeData = card.getAttribute('data-type') || '';
    const matchQuery = searchData.includes(query);
    const matchType = (activeReportType === 'all') || (typeData === activeReportType);
    if (matchQuery && matchType) {{
      card.style.display = 'block';
      visibleCount++;
    }} else {{
      card.style.display = 'none';
    }}
  }});

  const emptyMsg = document.getElementById('report-empty');
  emptyMsg.style.display = visibleCount === 0 ? 'block' : 'none';

  const filtering = !!query || activeReportType !== 'all';
  const clearBtn = document.getElementById('search-clear');
  if (clearBtn) clearBtn.style.display = query ? 'block' : 'none';
  const countEl = document.getElementById('search-count');
  if (countEl) countEl.textContent = filtering ? ('匹配到 ' + visibleCount + ' 条研报') : '';

  // 分组标签在筛选时隐藏
  document.querySelectorAll('.date-group').forEach(function (g) {{
    g.style.display = filtering ? 'none' : 'flex';
  }});
}}

// 研报分类胶囊（个股研报 / 行业研报 / 产业分析）
function filterReportType(type, btn) {{
  activeReportType = type;
  document.querySelectorAll('#report-type-bar .filter-btn').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');
  filterReports();
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

    icon_path = os.path.join(os.path.dirname(OUTPUT_FILE), "icon.png")
    with open(icon_path, "wb") as f:
        f.write(base64.b64decode(ICON_PNG_B64))

    report_path = os.path.join(os.path.dirname(OUTPUT_FILE), "report.html")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(build_report_page(reports_data))

    print(f"已生成 {OUTPUT_FILE}，前端交互已全面优化。")
    print(f"已生成 {report_path}，共 {len(reports_data)} 篇研报详情。")
    print(f"已生成 {icon_path}。")


if __name__ == "__main__":
    main()

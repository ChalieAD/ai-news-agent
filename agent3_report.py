"""
Agent 3 — Report Generator
Reads today's scored items and produces a dark-themed HTML report:
  "Jarvis AI Briefing — [date]"

Sections by category, each item shows title, source, score badge, reason, link.
Maximum 10 items displayed.

Output: reports/briefing_YYYY-MM-DD.html
"""

import json
import math
from datetime import date, datetime
from pathlib import Path


MAX_ITEMS = 10

CATEGORY_META = {
    "NEW_TOOL":     {"label": "New Tool",       "color": "#8b5cf6", "icon": "⚡"},
    "TUTORIAL":     {"label": "Tutorial",        "color": "#3b82f6", "icon": "📖"},
    "BUSINESS_OPP": {"label": "Business Opp",   "color": "#10b981", "icon": "💰"},
    "JUST_NEWS":    {"label": "Just News",       "color": "#64748b", "icon": "📰"},
}

SOURCE_COLORS = {
    "HackerNews":         "#f97316",
    "ProductHunt":        "#da4f26",
    "Reddit r/artificial": "#ff4500",
}


# ── Load ──────────────────────────────────────────────────────────────────────

def load_latest(data_dir: str = "data") -> list[dict]:
    files = sorted(Path(data_dir).glob("scored_*.json"), reverse=True)
    if not files:
        raise FileNotFoundError(
            f"No scored files in '{data_dir}/'. Run agent2_score.py first."
        )
    path = files[0]
    print(f"  Loading: {path}")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ── HTML builder ──────────────────────────────────────────────────────────────

def _score_badge(score: int) -> str:
    if score >= 9:
        color = "#10b981"
    elif score >= 7:
        color = "#3b82f6"
    else:
        color = "#f59e0b"
    return (
        f'<span class="score-badge" '
        f'style="background:{color}22;color:{color};border:1px solid {color}66">'
        f'{score}/10</span>'
    )


def _source_badge(source: str) -> str:
    color = SOURCE_COLORS.get(source, "#94a3b8")
    return (
        f'<span class="source-badge" '
        f'style="background:{color}18;color:{color};border:1px solid {color}44">'
        f'{source}</span>'
    )


def _action_badge(action: bool) -> str:
    if not action:
        return ""
    return '<span class="action-badge">ACTION</span>'


def _item_card(item: dict) -> str:
    cat   = item.get("ai_category", "JUST_NEWS")
    meta  = CATEGORY_META.get(cat, CATEGORY_META["JUST_NEWS"])
    title = item.get("title", "Untitled")
    url   = item.get("url", "#")
    score = item.get("ai_score", 0)
    reason = item.get("ai_reason", "")
    source = item.get("source", "")
    action = item.get("action_required", False)

    # Truncate long titles
    display_title = title if len(title) <= 110 else title[:107] + "…"

    return f"""
      <div class="item-card" data-category="{cat}">
        <div class="item-header">
          <div class="item-badges">
            {_source_badge(source)}
            {_score_badge(score)}
            {_action_badge(action)}
          </div>
          <div class="item-cat" style="color:{meta['color']}">{meta['icon']} {meta['label']}</div>
        </div>
        <a href="{url}" class="item-title" target="_blank" rel="noopener">{display_title}</a>
        <p class="item-reason">{reason}</p>
        <a href="{url}" class="item-link" target="_blank" rel="noopener">
          Read more -&gt;
        </a>
      </div>"""


def _section(category: str, items: list[dict]) -> str:
    if not items:
        return ""
    meta = CATEGORY_META.get(category, CATEGORY_META["JUST_NEWS"])
    cards = "".join(_item_card(i) for i in items)
    return f"""
    <div class="section">
      <div class="section-title">
        <span style="color:{meta['color']}">{meta['icon']}</span>
        {meta['label']}
        <span class="section-count">{len(items)}</span>
      </div>
      <div class="items-grid">
        {cards}
      </div>
    </div>"""


def build_html(items: list[dict]) -> str:
    today      = date.today()
    date_str   = today.isoformat()
    date_fmt   = today.strftime("%B %d, %Y")
    day_name   = today.strftime("%A")

    # Cap at MAX_ITEMS (already sorted by score desc)
    items = items[:MAX_ITEMS]

    # KPI counts
    categories = list(CATEGORY_META.keys())
    cat_counts = {c: sum(1 for i in items if i.get("ai_category") == c) for c in categories}
    action_count = sum(1 for i in items if i.get("action_required"))
    avg_score = round(sum(i.get("ai_score", 0) for i in items) / len(items), 1) if items else 0

    # Group items by category
    by_cat = {c: [i for i in items if i.get("ai_category") == c] for c in categories}

    kpi_cards = f"""
    <div class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-value">{len(items)}</div>
        <div class="kpi-label">Items Today</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-value">{avg_score}</div>
        <div class="kpi-label">Avg Score</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-value" style="color:#8b5cf6">{cat_counts['NEW_TOOL']}</div>
        <div class="kpi-label">New Tools</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-value" style="color:#10b981">{cat_counts['BUSINESS_OPP']}</div>
        <div class="kpi-label">Biz Opps</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-value" style="color:#f97316">{action_count}</div>
        <div class="kpi-label">Action Required</div>
      </div>
    </div>"""

    # Sections in priority order
    sections_html = ""
    for cat in ["NEW_TOOL", "BUSINESS_OPP", "TUTORIAL", "JUST_NEWS"]:
        sections_html += _section(cat, by_cat[cat])

    # Source breakdown
    sources = {}
    for item in items:
        s = item.get("source", "Unknown")
        sources[s] = sources.get(s, 0) + 1
    source_pills = "".join(
        f'<span class="source-pill" style="color:{SOURCE_COLORS.get(s, "#94a3b8")};'
        f'border-color:{SOURCE_COLORS.get(s, "#94a3b8")}44">{s} ({n})</span>'
        for s, n in sources.items()
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Jarvis AI Briefing — {date_fmt}</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

  :root {{
    --bg:       #0f172a;
    --surface:  #1e293b;
    --surface2: #273449;
    --border:   #334155;
    --text:     #f1f5f9;
    --muted:    #94a3b8;
    --accent:   #f97316;
    --accent2:  #3b82f6;
  }}

  body {{
    font-family: 'Inter', system-ui, sans-serif;
    background: var(--bg);
    color: var(--text);
    font-size: 14px;
    line-height: 1.6;
  }}

  .page {{ max-width: 1000px; margin: 0 auto; padding: 40px 24px 80px; }}

  /* ── Header ── */
  .header {{
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    padding: 40px 48px;
    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
    border: 1px solid var(--border);
    border-radius: 16px;
    margin-bottom: 32px;
    position: relative;
    overflow: hidden;
  }}
  .header::before {{
    content: '';
    position: absolute;
    top: -60px; right: -60px;
    width: 240px; height: 240px;
    background: radial-gradient(circle, #f9731618 0%, transparent 70%);
    pointer-events: none;
  }}
  .header-left h1 {{
    font-size: 26px;
    font-weight: 800;
    letter-spacing: -0.5px;
    margin-bottom: 6px;
  }}
  .header-left h1 span {{ color: var(--accent); }}
  .header-left .sub {{ color: var(--muted); font-size: 13px; margin-top: 4px; }}
  .header-right {{ text-align: right; flex-shrink: 0; }}
  .header-right .date-big {{ font-size: 15px; font-weight: 700; margin-bottom: 4px; }}
  .header-right .date-day {{ font-size: 12px; color: var(--muted); margin-bottom: 8px; }}
  .powered-by {{
    font-size: 11px;
    color: var(--border);
    background: var(--surface2);
    padding: 4px 10px;
    border-radius: 20px;
    border: 1px solid var(--border);
  }}

  /* ── KPIs ── */
  .kpi-grid {{
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 16px;
    margin-bottom: 32px;
  }}
  .kpi-card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 20px 16px;
    text-align: center;
    transition: border-color .2s;
  }}
  .kpi-card:hover {{ border-color: var(--accent); }}
  .kpi-value {{
    font-size: 28px;
    font-weight: 800;
    color: var(--text);
    letter-spacing: -1px;
    line-height: 1;
    margin-bottom: 6px;
  }}
  .kpi-label {{
    font-size: 11px;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.8px;
  }}

  /* ── Source row ── */
  .source-row {{
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    margin-bottom: 32px;
  }}
  .source-pill {{
    font-size: 11px;
    font-weight: 600;
    padding: 4px 12px;
    border-radius: 20px;
    border: 1px solid;
    background: transparent;
  }}

  /* ── Section ── */
  .section {{ margin-bottom: 36px; }}
  .section-title {{
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    color: var(--accent);
    margin-bottom: 16px;
    display: flex;
    align-items: center;
    gap: 8px;
  }}
  .section-title::after {{
    content: '';
    flex: 1;
    height: 1px;
    background: var(--border);
  }}
  .section-count {{
    background: var(--surface2);
    border: 1px solid var(--border);
    color: var(--muted);
    padding: 1px 8px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 600;
  }}

  /* ── Item cards ── */
  .items-grid {{ display: flex; flex-direction: column; gap: 12px; }}
  .item-card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 18px 20px;
    transition: border-color .2s, transform .15s;
  }}
  .item-card:hover {{
    border-color: #475569;
    transform: translateY(-1px);
  }}
  .item-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 10px;
  }}
  .item-badges {{ display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }}
  .score-badge, .source-badge {{
    display: inline-block;
    padding: 2px 8px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 700;
    white-space: nowrap;
  }}
  .action-badge {{
    display: inline-block;
    padding: 2px 8px;
    border-radius: 20px;
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 0.8px;
    background: #f9731622;
    color: var(--accent);
    border: 1px solid #f9731644;
    animation: pulse 2s infinite;
  }}
  @keyframes pulse {{
    0%, 100% {{ opacity: 1; }}
    50%       {{ opacity: 0.6; }}
  }}
  .item-cat {{
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.8px;
  }}
  .item-title {{
    display: block;
    font-size: 14px;
    font-weight: 600;
    color: var(--text);
    text-decoration: none;
    margin-bottom: 8px;
    line-height: 1.4;
  }}
  .item-title:hover {{ color: var(--accent); }}
  .item-reason {{
    font-size: 12px;
    color: var(--muted);
    line-height: 1.5;
    margin-bottom: 10px;
  }}
  .item-link {{
    font-size: 11px;
    font-weight: 600;
    color: var(--accent2);
    text-decoration: none;
    letter-spacing: 0.3px;
  }}
  .item-link:hover {{ text-decoration: underline; }}

  /* ── Footer ── */
  .footer {{
    text-align: center;
    color: var(--border);
    font-size: 11px;
    margin-top: 48px;
    padding-top: 24px;
    border-top: 1px solid var(--border);
  }}

  @media (max-width: 640px) {{
    .kpi-grid {{ grid-template-columns: repeat(3, 1fr); }}
    .header {{ flex-direction: column; gap: 16px; padding: 24px; }}
    .header-right {{ text-align: left; }}
  }}
</style>
</head>
<body>
<div class="page">

  <!-- Header -->
  <div class="header">
    <div class="header-left">
      <h1>Jarvis <span>AI Briefing</span></h1>
      <div class="sub">Your daily AI intelligence digest — scored for relevance by LLaMA 3.3 70B</div>
    </div>
    <div class="header-right">
      <div class="date-big">{date_fmt}</div>
      <div class="date-day">{day_name}</div>
      <div class="powered-by">Powered by Groq · LLaMA 3.3 70B</div>
    </div>
  </div>

  <!-- KPIs -->
  {kpi_cards}

  <!-- Source breakdown -->
  <div class="source-row">{source_pills}</div>

  <!-- Sections -->
  {sections_html}

  <!-- Footer -->
  <div class="footer">
    Jarvis AI Briefing &nbsp;·&nbsp; {date_fmt} &nbsp;·&nbsp;
    Sources: HackerNews · ProductHunt · Reddit r/artificial &nbsp;·&nbsp;
    Scored by Groq / LLaMA 3.3 70B
  </div>

</div>
</body>
</html>"""


# ── Entry point ───────────────────────────────────────────────────────────────

def run() -> str:
    print(f"\n{'='*60}")
    print("  AGENT 3 -- REPORT GENERATOR")
    print(f"{'='*60}\n")

    items = load_latest()
    print(f"  {len(items)} scored items loaded")
    print(f"  Showing top {min(len(items), MAX_ITEMS)} items\n")

    html = build_html(items)

    date_str = date.today().isoformat()
    out_dir  = Path("reports")
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"briefing_{date_str}.html"

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"  Saved: {out_path}")
    print(f"\n  Open in browser:")
    print(f"  {out_path.resolve()}\n")
    return str(out_path)


if __name__ == "__main__":
    run()

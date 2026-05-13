"""HTML rendering helpers for the front end.

No template engine — small string-builder helpers that produce safe,
HTML-escaped output. CSS lives inline in the page shell so a single
response is sufficient and there's no static-asset deploy step.
"""

from __future__ import annotations

import html
from collections.abc import Iterable, Sequence
from datetime import date, datetime
from decimal import Decimal
from typing import Any

NAV = [
    ("/", "Home"),
    ("/ui/postings", "Postings"),
    ("/ui/organizations", "Organizations"),
    ("/ui/compensation", "Compensation"),
    ("/ui/projects", "Projects"),
    ("/ui/lmi", "Labor market"),
    ("/ui/sources", "Sources"),
    ("/docs", "API"),
]


CSS = """
:root {
  --bg:#0b0d12; --bg-elev:#161922; --bg-elev-2:#1d212c;
  --border:#272d39; --border-strong:#3a4150;
  --text:#e6e8ed; --text-muted:#8a92a3; --text-faint:#5d6478;
  --accent:#5bc0de; --accent-strong:#88e0f0; --accent-dim:rgba(91,192,222,0.18);
  --good:#4ade80; --warn:#fbbf24; --danger:#f87171;
  --shadow:0 1px 2px rgba(0,0,0,.4), 0 8px 24px rgba(0,0,0,.18);
}
* { box-sizing: border-box; }
html,body { margin:0; padding:0; }
body {
  background:var(--bg); color:var(--text);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Inter,Helvetica,Arial,sans-serif;
  font-size:14px; line-height:1.5;
  -webkit-font-smoothing:antialiased;
}
a { color:var(--accent); text-decoration:none; }
a:hover { color:var(--accent-strong); }
.container { max-width:1280px; margin:0 auto; padding:0 24px; }

.topbar {
  display:flex; align-items:center; gap:24px;
  padding:14px 24px; border-bottom:1px solid var(--border);
  background:rgba(11,13,18,0.8); position:sticky; top:0; z-index:10;
  backdrop-filter: blur(8px);
}
.brand { font-weight:700; font-size:14px; letter-spacing:0.02em; }
.brand .dot { color:var(--accent); }
nav { display:flex; gap:4px; flex:1; flex-wrap:wrap; }
nav a {
  color:var(--text-muted); padding:6px 10px;
  border-radius:6px; font-size:13px; font-weight:500;
}
nav a:hover { color:var(--text); background:var(--bg-elev); }
nav a.active { color:var(--text); background:var(--bg-elev); }

h1 { font-size:24px; font-weight:600; margin:28px 0 4px; letter-spacing:-0.01em; }
h2 { font-size:13px; font-weight:600; text-transform:uppercase; letter-spacing:0.06em;
     color:var(--text-muted); margin:32px 0 12px; }
.subtitle { color:var(--text-muted); margin-bottom:24px; font-size:14px; }

.stat-grid {
  display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr));
  gap:12px; margin-bottom:28px;
}
.stat {
  background:var(--bg-elev); border:1px solid var(--border); border-radius:10px;
  padding:14px 16px;
}
.stat-label {
  color:var(--text-muted); font-size:11px;
  text-transform:uppercase; letter-spacing:0.06em; font-weight:600;
}
.stat-value {
  font-size:24px; font-weight:600; margin-top:6px; letter-spacing:-0.02em;
}
.stat-sub { color:var(--text-faint); font-size:12px; margin-top:2px; }

table.data { width:100%; border-collapse:separate; border-spacing:0;
             background:var(--bg-elev); border:1px solid var(--border);
             border-radius:10px; overflow:hidden; }
table.data th {
  text-align:left; font-weight:500; color:var(--text-muted);
  font-size:11px; text-transform:uppercase; letter-spacing:0.06em;
  padding:11px 14px; background:var(--bg-elev-2);
  border-bottom:1px solid var(--border);
}
table.data td { padding:13px 14px; border-bottom:1px solid var(--border); vertical-align:top; }
table.data tr:last-child td { border-bottom:none; }
table.data tr.linked { cursor:pointer; transition:background 80ms ease; }
table.data tr.linked:hover { background:var(--bg-elev-2); }
table.data td.right { text-align:right; }
table.data th:first-child, table.data td:first-child {
  width:1%; white-space:nowrap; text-align:right;
  font-variant-numeric:tabular-nums; color:var(--text-faint);
}
table.data td a { color:var(--text); font-weight:500; }
table.data td a:hover { color:var(--accent-strong); }
.muted { color:var(--text-muted); }
.dim { color:var(--text-faint); }
.num { font-variant-numeric:tabular-nums; }

.card-grid {
  display:grid; grid-template-columns:repeat(auto-fill,minmax(320px,1fr));
  gap:14px;
}
.card {
  background:var(--bg-elev); border:1px solid var(--border); border-radius:10px;
  padding:18px; transition:border-color 80ms ease;
}
.card:hover { border-color:var(--border-strong); }
.card-title { font-size:15px; font-weight:600; margin:0 0 6px; letter-spacing:-0.01em; }
.card-title a { color:var(--text); }
.card-title a:hover { color:var(--accent-strong); }
.card-meta { color:var(--text-muted); font-size:12px; margin-bottom:10px; }
.card-summary { font-size:13px; color:var(--text); margin:8px 0 12px; line-height:1.55; }
.card-footer { display:flex; justify-content:space-between; align-items:center;
               font-size:12px; color:var(--text-muted); margin-top:12px; }

.pills { display:flex; flex-wrap:wrap; gap:4px; }
.pill {
  display:inline-block; background:var(--bg-elev-2);
  border:1px solid var(--border); border-radius:999px;
  padding:2px 9px; font-size:11px; color:var(--text-muted); font-weight:500;
  white-space:nowrap;
}
.pill.accent  { color:var(--accent); border-color:rgba(91,192,222,0.3); background:rgba(91,192,222,0.08); }
.pill.warn    { color:var(--warn);   border-color:rgba(251,191,36,0.3); background:rgba(251,191,36,0.08); }
.pill.good    { color:var(--good);   border-color:rgba(74,222,128,0.3); background:rgba(74,222,128,0.08); }
.pill.danger  { color:var(--danger); border-color:rgba(248,113,113,0.3); background:rgba(248,113,113,0.08); }
.pill.mono    { font-family:ui-monospace,SFMono-Regular,Menlo,monospace; }

.btn {
  display:inline-block; padding:9px 16px; border-radius:7px;
  background:var(--accent); color:#0b0d12 !important; font-weight:600;
  font-size:13px; letter-spacing:0.01em;
}
.btn:hover { background:var(--accent-strong); color:#0b0d12; }
.btn.ghost { background:transparent; color:var(--text) !important; border:1px solid var(--border); }
.btn.ghost:hover { background:var(--bg-elev); }

.detail-hero { margin:24px 0; }
.detail-hero h1 { font-size:28px; margin:0 0 6px; }
.detail-meta { color:var(--text-muted); margin-bottom:14px; }
.detail-summary { font-size:15px; line-height:1.6; color:var(--text); max-width:780px; }

.kv-grid {
  display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr));
  gap:10px 24px; margin:16px 0;
}
.kv-grid > div { padding:6px 0; border-bottom:1px solid var(--border); }
.kv-grid .k { color:var(--text-muted); font-size:11px;
              text-transform:uppercase; letter-spacing:0.06em; font-weight:600; }
.kv-grid .v { font-size:14px; margin-top:2px; }

.toolbar {
  display:flex; gap:8px; flex-wrap:wrap; margin:6px 0 16px;
  align-items:center;
}
.toolbar form { display:flex; gap:6px; flex-wrap:wrap; }
.toolbar input, .toolbar select {
  background:var(--bg-elev); color:var(--text);
  border:1px solid var(--border); border-radius:6px;
  padding:6px 10px; font:inherit; font-size:13px;
}
.toolbar input:focus, .toolbar select:focus { outline:none; border-color:var(--accent); }
.toolbar button {
  background:var(--bg-elev); color:var(--text); border:1px solid var(--border);
  border-radius:6px; padding:6px 12px; font:inherit; font-size:13px;
  cursor:pointer;
}
.toolbar button:hover { background:var(--bg-elev-2); }

.empty {
  background:var(--bg-elev); border:1px dashed var(--border);
  border-radius:10px; padding:28px; text-align:center; color:var(--text-muted);
}

footer {
  color:var(--text-faint); font-size:12px; padding:24px 0;
  border-top:1px solid var(--border); margin-top:48px;
}
"""


def page(title: str, body: str, *, current_path: str = "/", subtitle: str | None = None) -> str:
    nav_html = "".join(
        f'<a href="{html.escape(href)}"'
        + (' class="active"' if href == current_path else "")
        + f'>{html.escape(label)}</a>'
        for href, label in NAV
    )
    sub_html = f'<div class="subtitle">{html.escape(subtitle)}</div>' if subtitle else ""
    return (
        '<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
        f'<title>{html.escape(title)} — LIP</title>'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<style>{CSS}</style></head><body>'
        '<header class="topbar">'
        '<div class="brand">labor<span class="dot">·</span>intel</div>'
        f'<nav>{nav_html}</nav></header>'
        '<main class="container">'
        f'<h1>{html.escape(title)}</h1>'
        f'{sub_html}'
        f'{body}'
        '</main>'
        '<footer class="container">'
        'Industrial labor intelligence — construction · energy · industrial · trades. '
        'Canada coverage primary; US coverage rolling.'
        '</footer>'
        '</body></html>'
    )


# -- primitive components -------------------------------------------------------


def stat(label: str, value: Any, *, sub: str | None = None) -> str:
    return (
        '<div class="stat">'
        f'<div class="stat-label">{html.escape(label)}</div>'
        f'<div class="stat-value num">{html.escape(_fmt(value))}</div>'
        + (f'<div class="stat-sub">{html.escape(sub)}</div>' if sub else '')
        + '</div>'
    )


def stat_grid(items: Iterable[str]) -> str:
    return f'<div class="stat-grid">{"".join(items)}</div>'


def pill(text: Any, *, variant: str = "") -> str:
    cls = "pill" + (f" {variant}" if variant else "")
    return f'<span class="{cls}">{html.escape(_fmt(text))}</span>'


def pills(values: Iterable[Any], *, variant: str = "") -> str:
    return '<div class="pills">' + "".join(pill(v, variant=variant) for v in values if v) + '</div>'


def card(*, title: str, meta: str = "", body_html: str = "", href: str | None = None,
         footer_left: str = "", footer_right: str = "") -> str:
    title_inner = (
        f'<a href="{html.escape(href)}">{html.escape(title)}</a>' if href else html.escape(title)
    )
    footer = ""
    if footer_left or footer_right:
        footer = (
            f'<div class="card-footer"><span>{footer_left}</span><span>{footer_right}</span></div>'
        )
    return (
        '<div class="card">'
        f'<div class="card-title">{title_inner}</div>'
        + (f'<div class="card-meta">{meta}</div>' if meta else "")
        + body_html
        + footer
        + '</div>'
    )


def card_grid(cards: Iterable[str]) -> str:
    return f'<div class="card-grid">{"".join(cards)}</div>'


def table(headers: Sequence[str], rows: Iterable[Sequence[Any]], *,
          right_align: Sequence[int] = (), numbered: bool = True) -> str:
    """Render a styled data table.

    With ``numbered=True`` (default) the leading column is a 1-based row
    index. Right-align indices in ``right_align`` are 0-based against
    ``headers`` (i.e. counted *after* the row-number column is added).

    Cell values are escaped here; if a cell needs to embed pre-built
    HTML, wrap it in ``Raw(html_string)``.
    """
    if numbered:
        headers = ("#", *headers)
        right_align = tuple({0, *right_align})  # always right-align the index

    head = "<tr>" + "".join(f"<th>{html.escape(h)}</th>" for h in headers) + "</tr>"

    body = []
    for idx, row in enumerate(rows, start=1):
        link = row[0].link if row and isinstance(row[0], LinkedRow) else None
        data_cells = list(row[1:] if link else row)
        if numbered:
            data_cells = [Raw(f'<span class="muted num">{idx}</span>'), *data_cells]
        cells = []
        for i, v in enumerate(data_cells):
            cls = " class=\"right\"" if i in right_align else ""
            cells.append(f"<td{cls}>{_cell(v)}</td>")
        attrs = (' class="linked" onclick="window.location=\'' + html.escape(link) + '\'"'
                 if link else "")
        body.append(f"<tr{attrs}>" + "".join(cells) + "</tr>")
    return f'<table class="data"><thead>{head}</thead><tbody>{"".join(body)}</tbody></table>'


class Raw:
    """Mark a value as already-HTML-safe (won't be re-escaped by _cell)."""
    __slots__ = ("html",)

    def __init__(self, html_str: str) -> None:
        self.html = html_str


class LinkedRow:
    """Wraps the first cell of a table row to make the whole row clickable."""
    __slots__ = ("link",)

    def __init__(self, link: str) -> None:
        self.link = link


def kv(label: str, value: Any) -> str:
    if value is None or value == "":
        return ""
    return (
        f'<div><div class="k">{html.escape(label)}</div>'
        f'<div class="v">{_cell(value)}</div></div>'
    )


def kv_grid(items: Iterable[str]) -> str:
    return f'<div class="kv-grid">{"".join(s for s in items if s)}</div>'


def empty_state(noun: str, hint: str | None = None) -> str:
    msg = f"No {noun} yet."
    if hint:
        msg += f" {hint}"
    return f'<div class="empty">{html.escape(msg)}</div>'


# -- formatting -----------------------------------------------------------------


def _cell(value: Any) -> str:
    if isinstance(value, Raw):
        return value.html
    return html.escape(_fmt(value))


def _fmt(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return f"{value:,.0f}" if value == value.to_integral() else f"{value:,.2f}"
    if isinstance(value, float):
        return f"{value:,.2f}"
    if isinstance(value, int):
        return f"{value:,}"
    if isinstance(value, list):
        return ", ".join(str(v) for v in value) if value else "—"
    return str(value)


def fmt_money(value: Decimal | float | None, currency: str | None = None) -> str:
    if value is None:
        return "—"
    v = float(value)
    if v >= 1_000_000_000:
        return f"${v / 1_000_000_000:.1f}B {currency or ''}".rstrip()
    if v >= 1_000_000:
        return f"${v / 1_000_000:.1f}M {currency or ''}".rstrip()
    if v >= 1_000:
        return f"${v / 1_000:.0f}k {currency or ''}".rstrip()
    return f"${v:,.0f} {currency or ''}".rstrip()


def fmt_salary(low, high, currency=None, period=None) -> str:
    if low is None and high is None:
        return "—"
    cur = currency or ""
    per = f"/{period[:3]}" if period and period != "annual" else "/yr"
    if low is not None and high is not None:
        return f"${float(low) / 1000:.0f}k–${float(high) / 1000:.0f}k {cur}{per}"
    one = low if low is not None else high
    return f"${float(one) / 1000:.0f}k {cur}{per}"


def shortage_pill(value: Decimal | float | None) -> str:
    if value is None:
        return pill("—")
    v = float(value)
    if v >= 0.78:
        return pill(f"{v:.2f}", variant="danger")
    if v >= 0.60:
        return pill(f"{v:.2f}", variant="warn")
    return pill(f"{v:.2f}", variant="good")

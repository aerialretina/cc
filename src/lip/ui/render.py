"""Text-table + page rendering helpers.

The UI emits a single ``<pre>``-wrapped page per route so a browser
renders it as monospace text. Keeping templating in pure Python avoids
the Jinja2 dependency and keeps the surface tiny.
"""

from __future__ import annotations

import html
from collections.abc import Iterable, Sequence
from datetime import date, datetime
from decimal import Decimal
from typing import Any

NAV = [
    ("/", "home"),
    ("/ui/postings", "postings"),
    ("/ui/organizations", "organizations"),
    ("/ui/compensation", "compensation"),
    ("/ui/projects", "projects"),
    ("/ui/lmi", "lmi"),
    ("/docs", "api docs"),
]


def page(title: str, body: str) -> str:
    """Wrap a rendered body in a minimal HTML shell.

    Note: ``body`` is expected to be already-escaped or hand-formatted as
    HTML inside a ``<pre>`` block.
    """
    nav_html = "  ".join(
        f'<a href="{html.escape(href)}">{html.escape(label)}</a>'
        for href, label in NAV
    )
    return (
        "<!doctype html>\n"
        f"<html><head><meta charset=\"utf-8\"><title>{html.escape(title)}</title>"
        "<style>"
        "body{background:#0f1115;color:#d8dee9;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;"
        "max-width:1100px;margin:24px auto;padding:0 16px;line-height:1.45}"
        "a{color:#88c0d0;text-decoration:none}a:hover{text-decoration:underline}"
        "nav{border-bottom:1px solid #2e3440;padding-bottom:8px;margin-bottom:16px}"
        "h1{font-size:1.1rem;margin:0 0 8px 0;color:#eceff4}"
        "pre{white-space:pre-wrap;word-break:break-word;margin:0}"
        ".muted{color:#6c7a89}"
        "</style></head><body>"
        f"<nav>{nav_html}</nav>"
        f"<h1>{html.escape(title)}</h1>"
        f"<pre>{body}</pre>"
        "</body></html>"
    )


def text_table(headers: Sequence[str], rows: Iterable[Sequence[Any]]) -> str:
    """Render a fixed-width plaintext table. Output is HTML-escaped."""
    rendered_rows = [[_cell(v) for v in row] for row in rows]
    cols = list(headers)
    widths = [len(h) for h in cols]
    for row in rendered_rows:
        for i, cell in enumerate(row):
            if i < len(widths):
                widths[i] = max(widths[i], len(cell))

    def fmt_row(values: Sequence[str]) -> str:
        return "  ".join(v.ljust(widths[i]) for i, v in enumerate(values))

    sep = "  ".join("-" * w for w in widths)
    out = [fmt_row(cols), sep]
    for row in rendered_rows:
        out.append(fmt_row(row))
    return html.escape("\n".join(out))


def empty_state(noun: str, hint: str | None = None) -> str:
    msg = f"No {noun} yet."
    if hint:
        msg += f" {hint}"
    return f'<span class="muted">{html.escape(msg)}</span>'


def kv_block(pairs: Iterable[tuple[str, Any]]) -> str:
    """Render a key/value list as ``key : value`` lines, HTML-escaped."""
    lines = []
    label_w = 0
    materialized = list(pairs)
    for k, _ in materialized:
        label_w = max(label_w, len(k))
    for k, v in materialized:
        lines.append(f"{k.ljust(label_w)} : {_cell(v)}")
    return html.escape("\n".join(lines))


def _cell(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return f"{value:,.2f}"
    if isinstance(value, float):
        return f"{value:,.2f}"
    if isinstance(value, list):
        return ", ".join(str(v) for v in value) if value else "—"
    return str(value)

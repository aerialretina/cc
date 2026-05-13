"""Shared HTTP client construction.

Centralizes user-agent + proxy wiring so every spider picks up
``LIP_PROXY_URL`` without duplicating ``httpx.Client(...)`` boilerplate.

Set ``LIP_PROXY_URL`` to a residential / mobile proxy endpoint
(Bright Data, Oxylabs, Smartproxy, etc.) to route spider traffic
through consumer IPs and bypass the bot detection that blocks
datacenter egress.
"""

from __future__ import annotations

import httpx

from lip.config import get_settings


def make_http_client(
    *,
    timeout: float = 15.0,
    accept: str = "application/json, text/html;q=0.9",
    extra_headers: dict[str, str] | None = None,
) -> httpx.Client:
    settings = get_settings()
    headers = {
        "User-Agent": settings.scrape_user_agent,
        "Accept": accept,
    }
    if extra_headers:
        headers.update(extra_headers)
    return httpx.Client(
        timeout=timeout,
        headers=headers,
        follow_redirects=True,
        proxy=settings.proxy_url or None,
    )

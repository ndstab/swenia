"""Fetching from RSS, arXiv, and Hacker News. Best-effort: failures are non-fatal."""

from __future__ import annotations

from datetime import datetime, timezone

import feedparser
import httpx

from . import config as cfg
from .models import Item


def _clean(text: str, limit: int = 600) -> str:
    return " ".join((text or "").split())[:limit]


def _published(entry) -> datetime | None:
    for attr in ("published_parsed", "updated_parsed"):
        t = entry.get(attr)
        if t:
            return datetime(*t[:6], tzinfo=timezone.utc)
    return None


def fetch_rss(client: httpx.Client, log) -> list[Item]:
    out: list[Item] = []
    for name, url in cfg.RSS_FEEDS:
        try:
            r = client.get(url, timeout=cfg.FETCH_TIMEOUT, follow_redirects=True)
            r.raise_for_status()
            parsed = feedparser.parse(r.content)
            for e in parsed.entries[:15]:
                out.append(Item(
                    source=name,
                    title=_clean(e.get("title", ""), 300),
                    snippet=_clean(e.get("summary", ""), 600),
                    url=e.get("link", ""),
                    published=_published(e),
                ))
            log(f"[green]✓[/] {name}: {len(parsed.entries[:15])} items")
        except Exception as ex:  # noqa: BLE001
            log(f"[yellow]⚠[/] {name} failed: {ex}")
    return out


def fetch_arxiv(client: httpx.Client, log) -> list[Item]:
    out: list[Item] = []
    for cat in cfg.ARXIV_CATEGORIES:
        try:
            r = client.get(
                "https://export.arxiv.org/api/query",
                params={
                    "search_query": f"cat:{cat}",
                    "sortBy": "submittedDate",
                    "sortOrder": "descending",
                    "max_results": cfg.ARXIV_PER_CAT,
                },
                timeout=20.0,
                follow_redirects=True,
            )
            r.raise_for_status()
            parsed = feedparser.parse(r.content)
            for e in parsed.entries:
                out.append(Item(
                    source=f"arXiv:{cat}",
                    title=_clean(e.get("title", ""), 300),
                    snippet=_clean(e.get("summary", ""), 600),
                    url=e.get("link", ""),
                    published=_published(e),
                ))
            log(f"[green]✓[/] arXiv {cat}: {len(parsed.entries)} items")
        except Exception as ex:  # noqa: BLE001
            log(f"[yellow]⚠[/] arXiv {cat} failed: {ex}")
    return out


def fetch_hn(client: httpx.Client, log) -> list[Item]:
    by_id: dict[str, Item] = {}
    for q in cfg.HN_QUERIES:
        try:
            r = client.get(
                "https://hn.algolia.com/api/v1/search",
                params={
                    "query": q,
                    "tags": "story",
                    "numericFilters": f"points>{cfg.HN_MIN_POINTS}",
                    "hitsPerPage": cfg.HN_PER_QUERY,
                },
                timeout=cfg.FETCH_TIMEOUT,
            )
            r.raise_for_status()
            for h in r.json().get("hits", []):
                oid = h.get("objectID")
                if not h.get("title") or oid in by_id:
                    continue
                ts = h.get("created_at_i")
                by_id[oid] = Item(
                    source=f"HN ({h.get('points', 0)}pts)",
                    title=_clean(h.get("title", ""), 300),
                    snippet=_clean(h.get("story_text") or h.get("title", ""), 400),
                    url=h.get("url") or f"https://news.ycombinator.com/item?id={oid}",
                    published=(datetime.fromtimestamp(ts, tz=timezone.utc) if ts else None),
                )
        except Exception as ex:  # noqa: BLE001
            log(f"[yellow]⚠[/] Hacker News '{q}' failed: {ex}")
    log(f"[green]✓[/] Hacker News: {len(by_id)} items")
    return list(by_id.values())


def fetch_all(client: httpx.Client, log) -> list[Item]:
    return fetch_rss(client, log) + fetch_arxiv(client, log) + fetch_hn(client, log)

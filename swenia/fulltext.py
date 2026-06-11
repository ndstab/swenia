"""
Full-text fetch — the accuracy fix.

The spike summarized from thin RSS teasers, which caused confident
confabulation (e.g. expanding 'RSI' as 'repetitive strain injury' and inventing
a story). Here we fetch the actual article and extract readable body text so the
summarizer works from real content. Every failure falls back to the snippet —
full text is an upgrade, never a hard dependency.
"""

from __future__ import annotations

import re

import httpx
import trafilatura

from . import config as cfg
from .models import Item

# arXiv abs pages: pull the abstract block specifically (the substance), rather
# than the whole HTML chrome or the PDF.
_ARXIV_ABS = re.compile(r'<blockquote class="abstract[^"]*">(.*?)</blockquote>',
                        re.DOTALL | re.IGNORECASE)
_TAGS = re.compile(r"<[^>]+>")


def _arxiv_abstract(html: str) -> str:
    m = _ARXIV_ABS.search(html)
    if not m:
        return ""
    text = _TAGS.sub(" ", m.group(1))
    text = text.replace("Abstract:", " ")
    return " ".join(text.split())


def fetch_one(client: httpx.Client, item: Item) -> str:
    """Return extracted article text for an item, or '' on any failure."""
    url = item.url
    if not url:
        return ""
    try:
        r = client.get(url, timeout=cfg.FETCH_TIMEOUT, follow_redirects=True)
        r.raise_for_status()
        html = r.text
    except Exception:  # noqa: BLE001 — best-effort; caller falls back to snippet
        return ""

    if "arxiv.org/abs" in url:
        text = _arxiv_abstract(html)
        if text:
            return text[: cfg.FULLTEXT_MAX_CHARS]
        # fall through to generic extraction if the regex missed

    try:
        extracted = trafilatura.extract(
            html, include_comments=False, include_tables=False, favor_recall=True
        ) or ""
    except Exception:  # noqa: BLE001
        extracted = ""
    return " ".join(extracted.split())[: cfg.FULLTEXT_MAX_CHARS]


def enrich(client: httpx.Client, items: list[Item], log) -> int:
    """Fill item.fulltext for each item. Returns count successfully enriched."""
    got = 0
    for it in items:
        text = fetch_one(client, it)
        if len(text) > len(it.snippet):   # only keep it if it's an actual upgrade
            it.fulltext = text
            got += 1
    log(f"[green]✓[/] full text: {got}/{len(items)} items enriched "
        f"[dim](rest fall back to snippet)[/]")
    return got

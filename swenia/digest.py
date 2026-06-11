"""
The digest contract — what the PWA reader fetches.

Writes output/latest.json and output/archive/YYYY-MM-DD.json. Cards are grouped
by category (headline / frontier) and ranked by score within each.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from . import config as cfg
from .models import Item

TIER_RANK = {"must_know": 0, "worth_knowing": 1, "skim": 2, "drop": 3}


def _summary_line(cards: list[Item]) -> str:
    mk = sum(1 for c in cards if c.tier == "must_know")
    wk = sum(1 for c in cards if c.tier == "worth_knowing")
    if not cards:
        return "Nothing new since you last checked — you're caught up."
    bits = []
    if mk:
        bits.append(f"{mk} must-know")
    if wk:
        bits.append(f"{wk} worth knowing")
    return " · ".join(bits) if bits else f"{len(cards)} items to skim."


def build(cards: list[Item], stamp: datetime | None = None) -> dict:
    """Build the digest dict. `stamp` is injected (Date.now is unavailable in
    some contexts) — defaults to now."""
    stamp = stamp or datetime.now(timezone.utc)

    def section(cat: str) -> list[dict]:
        rows = [c for c in cards if c.category == cat]
        rows.sort(key=lambda c: (TIER_RANK.get(c.tier, 9), -c.score))
        return [c.card_dict() for c in rows]

    headlines = section("headline")
    frontier = section("frontier")
    return {
        "date": stamp.date().isoformat(),
        "generated_at": stamp.isoformat(),
        "summary_line": _summary_line(cards),
        "counts": {
            "total": len(cards),
            "headlines": len(headlines),
            "frontier": len(frontier),
        },
        "sections": [
            {"key": "headlines", "title": "Headlines", "cards": headlines},
            {"key": "frontier", "title": "Frontier & Papers", "cards": frontier},
        ],
    }


def write(digest: dict) -> None:
    cfg.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    cfg.ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(digest, indent=2, ensure_ascii=False)
    cfg.LATEST_JSON.write_text(payload, encoding="utf-8")
    (cfg.ARCHIVE_DIR / f"{digest['date']}.json").write_text(payload, encoding="utf-8")

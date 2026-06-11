"""
Selection, clustering, and scoring.

  select()  — recency window + title dedup + per-source cap + round-robin balance
  cluster() — embeddings near-duplicate merge (collapses same-story variants)
  score()   — recency-decay × tier weight, used to rank within each section
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

import numpy as np

from . import config as cfg
from .models import Item, Source


def _base_source(source: str) -> str:
    return source.split(":")[0].split(" (")[0]


def _title_key(title: str) -> str:
    return "".join(c.lower() for c in title if c.isalnum())[:60]


def select(raw: list[Item], log) -> tuple[list[Item], dict]:
    """Recency-window, title-dedup, per-source cap, then round-robin interleave."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=cfg.RECENCY_DAYS)
    stats = {"raw": len(raw), "too_old": 0, "no_date": 0, "dup": 0}

    seen: set[str] = set()
    buckets: dict[str, list[Item]] = {}
    for it in raw:
        key = _title_key(it.title)
        if not key or key in seen:
            stats["dup"] += 1
            continue
        if it.published is None:
            stats["no_date"] += 1
        elif it.published < cutoff:
            stats["too_old"] += 1
            continue
        seen.add(key)
        buckets.setdefault(_base_source(it.source), []).append(it)

    floor = datetime.min.replace(tzinfo=timezone.utc)
    for b in buckets.values():
        b.sort(key=lambda it: it.published or floor, reverse=True)
        del b[cfg.MAX_PER_SOURCE:]

    items: list[Item] = []
    while any(buckets.values()) and len(items) < cfg.MAX_ITEMS_TO_FILTER:
        for b in buckets.values():
            if b:
                items.append(b.pop(0))
    stats["kept"] = len(items)
    stats["by_source"] = {s: sum(1 for it in items if _base_source(it.source) == s)
                          for s in buckets}
    log(f"[green]✓[/] selected {stats['kept']} (last {cfg.RECENCY_DAYS}d, "
        f"≤{cfg.MAX_PER_SOURCE}/src) from {stats['raw']} raw "
        f"[dim](dropped {stats['too_old']} stale, {stats['dup']} dup)[/]")
    return items, stats


def cluster(items: list[Item], log) -> list[Item]:
    """Merge near-duplicate stories via embeddings; keep one representative each,
    folding the others' sources into extra_sources."""
    if len(items) < 2:
        return items
    try:
        from fastembed import TextEmbedding
    except Exception as ex:  # noqa: BLE001
        log(f"[yellow]⚠[/] embeddings unavailable ({ex}); skipping dedup")
        return items

    texts = [f"{it.title}. {it.snippet}" for it in items]
    model = TextEmbedding(cfg.EMBED_MODEL)
    embs = np.array(list(model.embed(texts)), dtype=np.float32)
    embs /= np.linalg.norm(embs, axis=1, keepdims=True) + 1e-9
    sim = embs @ embs.T

    merged_into: list[int] = list(range(len(items)))  # union-find-ish parent
    used = [False] * len(items)
    reps: list[Item] = []
    for i in range(len(items)):
        if used[i]:
            continue
        used[i] = True
        rep = items[i]
        for j in range(i + 1, len(items)):
            if not used[j] and sim[i, j] >= cfg.DEDUP_THRESHOLD:
                used[j] = True
                rep.extra_sources.append(Source(items[j].source, items[j].url))
                # prefer the longer/fuller text as the representative body
                if len(items[j].snippet) > len(rep.snippet):
                    rep.snippet = items[j].snippet
        reps.append(rep)

    removed = len(items) - len(reps)
    log(f"[green]✓[/] clustering: {len(items)} → {len(reps)} "
        f"[dim]({removed} near-duplicates merged)[/]")
    return reps


def score(items: list[Item]) -> None:
    """Assign each item a recency-decay × tier-weight score (in place)."""
    now = datetime.now(timezone.utc)
    for it in items:
        age_days = ((now - it.published).total_seconds() / 86400.0
                    if it.published else 1.0)
        decay = math.exp(-max(age_days, 0.0) / cfg.DECAY_TAU_DAYS)
        it.score = cfg.TIER_WEIGHT.get(it.tier, 0.0) * decay

"""Core data structures and the digest JSON contract."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Source:
    name: str
    url: str


@dataclass
class Item:
    """One news item as it flows through the pipeline.

    Fields fill in across stages: fetch → select → filter → summarize.
    """
    source: str                       # display name of the originating feed
    title: str
    snippet: str                      # RSS teaser / abstract (always present)
    url: str
    published: datetime | None = None

    # populated by full-text fetch
    fulltext: str = ""                # extracted article body (may be empty)

    # populated by the filter
    tier: str = "drop"                # must_know | worth_knowing | skim | drop
    category: str = "frontier"        # headline | frontier
    reason: str = ""

    # populated by the card writer
    title_card: str = ""              # rewritten headline
    why: str = ""
    summary: str = ""
    tags: list[str] = field(default_factory=list)

    # populated by clustering / scoring
    extra_sources: list[Source] = field(default_factory=list)
    score: float = 0.0

    @property
    def id(self) -> str:
        """Stable content id — used as the seen-state key and card id."""
        return hashlib.sha1(self.url.encode("utf-8")).hexdigest()[:12]

    def card_dict(self) -> dict:
        """Serialize to the digest-contract card shape (Phase 2 reads this)."""
        sources = [{"name": self.source, "url": self.url}]
        sources += [{"name": s.name, "url": s.url} for s in self.extra_sources]
        return {
            "id": self.id,
            "tier": self.tier,
            "category": self.category,
            "title": self.title_card or self.title,
            "why_it_matters": self.why,
            "summary": self.summary,
            "tags": self.tags,
            "sources": sources,
            "published": self.published.isoformat() if self.published else None,
            "score": round(self.score, 4),
        }

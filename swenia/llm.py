"""
LLM stages: Haiku filter (tier + category) and Sonnet card-writer.

Each stage exposes a `*_messages()` builder (the request params) and an
`apply_*()` result handler, so the same logic drives both the synchronous path
(fast local iteration) and the Batch API path (50% cheaper, used in production).
"""

from __future__ import annotations

import json

from . import config as cfg
from .models import Item

# ── prompts ──────────────────────────────────────────────────────────────────

FILTER_SYSTEM = (
    "You are a sharp tech-news curator for ONE specific reader. "
    "Classify each item into a tier by IMPORTANCE TO THIS READER. "
    "Importance has TWO independent sources — weigh both:\n"
    "  (1) MAINSTREAM SIGNIFICANCE: will the whole field be talking about this? "
    "(flagship model launches, major capability jumps, big SOTA results, major "
    "lab announcements). Widely-covered != low value — these are big deals "
    "BECAUSE everyone discusses them.\n"
    "  (2) NICHE FRONTIER SIGNAL: technically deep, forward-looking work a "
    "researcher would find genuinely interesting.\n"
    "Tiers:\n"
    "- must_know: a major release/announcement the reader must not miss, OR a "
    "landmark technical result. The reader would regret missing it.\n"
    "- worth_knowing: relevant and substantive, but not field-defining. Most "
    "individual arXiv preprints land here.\n"
    "- skim: tangentially relevant or minor.\n"
    "- drop: sludge, off-topic, or in their NOT-interested list.\n"
    "Do NOT rank an obscure preprint above a flagship lab release. Reserve "
    "must_know for genuine big deals — don't inflate it.\n\n"
    "ALSO tag each item with a category:\n"
    "- headline: mainstream big-deal news the whole field discusses — model/"
    "product launches, major lab announcements, capability jumps, notable "
    "researcher news. (Newsletters, lab blogs, HN, big releases.)\n"
    "- frontier: deeper research & technical work — individual papers, new "
    "methods/architectures, niche results. (Most arXiv items are 'frontier'.)\n"
    "Tier and category are INDEPENDENT: a paper can be must_know+frontier; a "
    "launch can be must_know+headline.\n\n"
    f"READER PROFILE:\n{cfg.TASTE_PROFILE}"
)

CARDS_SYSTEM = (
    "You write inShorts-style news cards for ONE specific reader.\n"
    "For each item produce:\n"
    "- title: a crisp, specific headline (rewrite vague ones).\n"
    "- why_it_matters: ONE sentence on why THIS reader specifically should care, "
    "grounded in their profile.\n"
    "- summary: 40–60 words, dense and factual, no hype, no filler.\n"
    "- tags: 2–4 lowercase topical tags.\n"
    "Keep every id from the input.\n\n"
    "ACCURACY RULES — CRITICAL. The reader relies on these cards to be factually "
    "correct; a confident wrong summary is far worse than a vague one.\n"
    "- Use ONLY facts present in the provided text. Do NOT invent details, "
    "numbers, or claims not in the source.\n"
    "- Do NOT expand or guess acronyms unless the expansion is given in the "
    "source. If unsure, leave the acronym as-is. (In an AI/ML research context, "
    "default readings apply — 'RSI' = recursive self-improvement, 'RL' = "
    "reinforcement learning — never invent an unrelated meaning.)\n"
    "- If the text is too thin to summarize confidently, write a SHORTER, hedged "
    "summary of only what's stated rather than fabricating specifics.\n"
    "- When the source gives MULTIPLE numbers (e.g. a method beats X by 37% and Y "
    "by 48%), keep them DISTINCT — never merge two statistics into one or attribute "
    "one number to the wrong subject. When it reports per-metric or per-system "
    "rankings, don't flatten them into a single 'best' claim.\n\n"
    f"READER PROFILE:\n{cfg.TASTE_PROFILE}"
)

FILTER_SCHEMA = {
    "type": "object",
    "properties": {
        "results": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "tier": {"type": "string",
                             "enum": ["must_know", "worth_knowing", "skim", "drop"]},
                    "category": {"type": "string", "enum": ["headline", "frontier"]},
                    "reason": {"type": "string"},
                },
                "required": ["id", "tier", "category", "reason"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["results"],
    "additionalProperties": False,
}

CARDS_SCHEMA = {
    "type": "object",
    "properties": {
        "cards": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "title": {"type": "string"},
                    "why_it_matters": {"type": "string"},
                    "summary": {"type": "string"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["id", "title", "why_it_matters", "summary", "tags"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["cards"],
    "additionalProperties": False,
}


# ── request builders ───────────────────────────────────────────────────────────

def filter_messages(items: list[Item]) -> dict:
    listing = "\n".join(
        f"[{i}] ({it.source}) {it.title} — {it.snippet}" for i, it in enumerate(items)
    )
    return {
        "model": cfg.HAIKU,
        "max_tokens": 8000,
        "system": FILTER_SYSTEM,
        "messages": [{"role": "user",
                      "content": f"Classify these {len(items)} items:\n\n{listing}"}],
        "output_config": {"format": {"type": "json_schema", "schema": FILTER_SCHEMA}},
    }


def cards_messages(items: list[Item]) -> dict:
    # Use full text where we have it; fall back to the snippet otherwise.
    blocks = []
    for i, it in enumerate(items):
        body = it.fulltext if it.fulltext else it.snippet
        blocks.append(f"[{i}] ({it.source}) {it.title}\n{body}")
    listing = "\n\n---\n\n".join(blocks)
    return {
        "model": cfg.SONNET,
        "max_tokens": 8000,
        "system": CARDS_SYSTEM,
        "messages": [{"role": "user", "content": f"Write cards for these:\n\n{listing}"}],
        "output_config": {"format": {"type": "json_schema", "schema": CARDS_SCHEMA}},
    }


# ── result handlers ─────────────────────────────────────────────────────────────

def _text(resp) -> str:
    return next(b.text for b in resp.content if b.type == "text")


def apply_filter(items: list[Item], resp) -> None:
    data = json.loads(_text(resp))
    for r in data["results"]:
        i = r["id"]
        if 0 <= i < len(items):
            items[i].tier = r["tier"]
            items[i].category = r.get("category", "frontier")
            items[i].reason = r["reason"]


def apply_cards(items: list[Item], resp) -> None:
    data = json.loads(_text(resp))
    for c in data["cards"]:
        i = c["id"]
        if 0 <= i < len(items):
            it = items[i]
            it.title_card = c["title"]
            it.why = c["why_it_matters"]
            it.summary = c["summary"]
            it.tags = c["tags"]


def usd(model: str, usage) -> float:
    pin, pout = cfg.PRICES[model]
    return (usage.input_tokens * pin + usage.output_tokens * pout) / 1_000_000

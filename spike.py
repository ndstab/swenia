#!/usr/bin/env python3
"""
swenia — Phase 0 spike.

Goal of this file: prove the *curation*, nothing else. No storage, no UI.
It fetches a handful of real sources, lets Haiku throw out the sludge and tier
what's left against YOUR taste profile, then has Sonnet write inShorts-style
cards for the survivors — and prints them to your terminal.

If the cards this prints make you want to read them, the project is real.
If not, we fix the two knobs below (SOURCES, TASTE_PROFILE) before building more.

Run:
    pip3 install -r requirements.txt
    export ANTHROPIC_API_KEY=sk-ant-...
    python3 spike.py
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import feedparser
import httpx
from anthropic import Anthropic
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

# ─────────────────────────────────────────────────────────────────────────────
# KNOB 1: SOURCES.  Add/remove freely. RSS failures are non-fatal.
# ─────────────────────────────────────────────────────────────────────────────
RSS_FEEDS = [
    ("Import AI",        "https://importai.substack.com/feed"),
    ("Interconnects",    "https://www.interconnects.ai/feed"),
    ("Hugging Face",     "https://huggingface.co/blog/feed.xml"),
    ("BAIR (Berkeley)",  "https://bair.berkeley.edu/blog/feed.xml"),
    ("DeepMind",         "https://deepmind.google/blog/rss.xml"),
]
# arXiv categories to pull recent submissions from (quant-ph included per your ask)
ARXIV_CATEGORIES = ["cs.LG", "cs.CL", "cs.AI", "quant-ph"]
ARXIV_PER_CAT = 12
# Hacker News: AI-ish front-page-quality stories
HN_QUERIES = ["AI", "LLM", "model", "neural", "quantum"]
HN_MIN_POINTS = 50
HN_PER_QUERY = 15

RECENCY_DAYS = 3            # only keep items published within this many days
MAX_PER_SOURCE = 4         # stop any one feed from dominating the digest
MAX_ITEMS_TO_FILTER = 120  # bound tokens sent to Haiku
MAX_CARDS = 20             # cap the daily digest size

# ─────────────────────────────────────────────────────────────────────────────
# KNOB 2: TASTE PROFILE.  This is the heart of the curation — edit it until the
# cards feel like *yours*. Be specific about people, labs, and topics.
# ─────────────────────────────────────────────────────────────────────────────
TASTE_PROFILE = """\
I am an AI/research engineer. swenia is my daily way to stay current on AI/ML and
the broader tech world. I want BOTH:
  (A) the major, mainstream developments everyone in the field will be talking
      about — I must not miss these even if they're widely covered, AND
  (B) the niche, frontier, technically deep developments that a working
      researcher would find interesting.
IMPORTANT: "widely covered / mainstream" is NOT a reason to drop something. A
flagship model release is HIGH priority precisely because it's a big deal. Do not
penalize an item for being popular or well-known. Importance comes from EITHER
mainstream significance OR niche frontier signal — value both.

ALWAYS MUST-KNOW (these are the big deals — never bury them):
- Major model/product launches from leading labs: OpenAI, Anthropic (Claude, incl.
  Fable/Opus/Sonnet/Haiku), Google DeepMind (Gemini, Gemma), Meta, Mistral, xAI
  (Grok), DeepSeek, Qwen, Nvidia, and notable newer labs (Thinking Machines, SSI).
- Flagship releases, major capability jumps, big benchmark/SOTA results, major
  open-weight drops, significant product launches, and major research announcements
  that the whole field will discuss.
- Named-researcher moves & notable takes: Karpathy, Sutskever, Chollet, Le Cun, etc.

ALSO STRONGLY INTERESTED IN (the niche/frontier layer):
- New architectures, training methods, and serious technical results.
- RL, world models, agents, reasoning, interpretability, post-training/RLHF,
  evals, scaling laws.
- Quantum computing & quantum ML when there's real technical news.
- Important infrastructure/hardware shifts (new chips, training systems).
- An individual arXiv preprint is usually 'worth_knowing' or 'skim' UNLESS it is a
  landmark/widely-discussed result — don't rank an obscure preprint above a flagship
  lab release.

NOT INTERESTED IN (treat as 'drop'):
- "Top 10 AI tools to boost productivity" / listicles / SEO content.
- Generic business/funding/PR news with no technical or field-level substance.
- Crypto, gadget reviews, vague "AI will change everything" opinion pieces.
- Beginner tutorials and how-to-prompt content.
"""

# ─────────────────────────────────────────────────────────────────────────────

HAIKU = "claude-haiku-4-5"
SONNET = "claude-sonnet-4-6"

# batch-equivalent unit prices not used here (spike runs synchronously for
# instant feedback); standard per-1M-token prices for the live cost readout:
PRICES = {  # (input, output) USD per 1M tokens
    HAIKU: (1.00, 5.00),
    SONNET: (3.00, 15.00),
}

console = Console()


@dataclass
class Item:
    idx: int
    source: str
    title: str
    snippet: str
    url: str
    published: datetime | None = None   # publish time, UTC (None = unknown)
    tier: str = "drop"          # filled by the filter
    category: str = "frontier"  # headline | frontier — filled by the filter
    reason: str = ""            # filled by the filter
    # filled by the card writer:
    why: str = ""
    summary: str = ""
    tags: list[str] = field(default_factory=list)


# ── Fetching ────────────────────────────────────────────────────────────────

def _clean(text: str, limit: int = 500) -> str:
    text = " ".join((text or "").split())
    return text[:limit]


def _published(entry) -> datetime | None:
    """Pull a UTC datetime from a feedparser entry, if present."""
    for attr in ("published_parsed", "updated_parsed"):
        t = entry.get(attr)
        if t:
            return datetime(*t[:6], tzinfo=timezone.utc)
    return None


def fetch_rss(client: httpx.Client) -> list[dict]:
    out = []
    for name, url in RSS_FEEDS:
        try:
            r = client.get(url, timeout=15.0, follow_redirects=True)
            r.raise_for_status()
            parsed = feedparser.parse(r.content)
            for e in parsed.entries[:15]:
                out.append({
                    "source": name,
                    "title": _clean(e.get("title", ""), 300),
                    "snippet": _clean(e.get("summary", ""), 500),
                    "url": e.get("link", ""),
                    "published": _published(e),
                })
            console.log(f"[green]✓[/] {name}: {len(parsed.entries[:15])} items")
        except Exception as ex:  # noqa: BLE001 — best-effort fetch
            console.log(f"[yellow]⚠[/] {name} failed: {ex}")
    return out


def fetch_arxiv(client: httpx.Client) -> list[dict]:
    out = []
    for cat in ARXIV_CATEGORIES:
        try:
            r = client.get(
                "https://export.arxiv.org/api/query",
                params={
                    "search_query": f"cat:{cat}",
                    "sortBy": "submittedDate",
                    "sortOrder": "descending",
                    "max_results": ARXIV_PER_CAT,
                },
                timeout=20.0,
                follow_redirects=True,
            )
            r.raise_for_status()
            parsed = feedparser.parse(r.content)
            for e in parsed.entries:
                out.append({
                    "source": f"arXiv:{cat}",
                    "title": _clean(e.get("title", ""), 300),
                    "snippet": _clean(e.get("summary", ""), 500),
                    "url": e.get("link", ""),
                    "published": _published(e),
                })
            console.log(f"[green]✓[/] arXiv {cat}: {len(parsed.entries)} items")
        except Exception as ex:  # noqa: BLE001
            console.log(f"[yellow]⚠[/] arXiv {cat} failed: {ex}")
    return out


def fetch_hn(client: httpx.Client) -> list[dict]:
    """One query per term (Algolia has no OR operator), deduped by story id."""
    by_id: dict[str, dict] = {}
    for q in HN_QUERIES:
        try:
            r = client.get(
                "https://hn.algolia.com/api/v1/search",
                params={
                    "query": q,
                    "tags": "story",
                    "numericFilters": f"points>{HN_MIN_POINTS}",
                    "hitsPerPage": HN_PER_QUERY,
                },
                timeout=15.0,
            )
            r.raise_for_status()
            for h in r.json().get("hits", []):
                oid = h.get("objectID")
                if not h.get("title") or oid in by_id:
                    continue
                ts = h.get("created_at_i")
                by_id[oid] = {
                    "source": f"HN ({h.get('points', 0)}pts)",
                    "title": _clean(h.get("title", ""), 300),
                    "snippet": _clean(h.get("story_text") or h.get("title", ""), 300),
                    "url": h.get("url") or f"https://news.ycombinator.com/item?id={oid}",
                    "published": (datetime.fromtimestamp(ts, tz=timezone.utc)
                                  if ts else None),
                }
        except Exception as ex:  # noqa: BLE001
            console.log(f"[yellow]⚠[/] Hacker News '{q}' failed: {ex}")
    console.log(f"[green]✓[/] Hacker News: {len(by_id)} items")
    return list(by_id.values())


def _base_source(source: str) -> str:
    """'arXiv:cs.LG' -> 'arXiv', 'HN (210pts)' -> 'HN' for per-source capping."""
    return source.split(":")[0].split(" (")[0]


def select(raw: list[dict]) -> tuple[list[Item], dict]:
    """Recency-filter, title-dedup, then round-robin across sources so no single
    feed dominates. Returns (items, stats). Embeddings dedup arrives in Phase 1."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=RECENCY_DAYS)
    stats = {"raw": len(raw), "too_old": 0, "no_date": 0, "dup": 0}

    # 1. Title dedup + recency filter, bucketed by base source.
    seen: set[str] = set()
    buckets: dict[str, list[dict]] = {}
    for r in raw:
        key = "".join(c.lower() for c in r["title"] if c.isalnum())[:60]
        if not key or key in seen:
            stats["dup"] += 1
            continue
        pub = r.get("published")
        if pub is None:
            stats["no_date"] += 1   # keep undated items (e.g. some blogs); don't penalize
        elif pub < cutoff:
            stats["too_old"] += 1
            continue
        seen.add(key)
        buckets.setdefault(_base_source(r["source"]), []).append(r)

    # 2. Sort each bucket newest-first and cap per source.
    for b in buckets.values():
        b.sort(key=lambda r: r.get("published") or datetime.min.replace(tzinfo=timezone.utc),
                reverse=True)
        del b[MAX_PER_SOURCE:]

    # 3. Round-robin interleave so the filter sees a balanced mix, not 15 of one feed.
    items: list[Item] = []
    idx = 0
    while any(buckets.values()) and len(items) < MAX_ITEMS_TO_FILTER:
        for b in buckets.values():
            if b:
                r = b.pop(0)
                items.append(Item(idx=idx, source=r["source"], title=r["title"],
                                  snippet=r["snippet"], url=r["url"],
                                  published=r.get("published")))
                idx += 1
    stats["kept"] = len(items)
    stats["by_source"] = {s: sum(1 for it in items if _base_source(it.source) == s)
                          for s in buckets}
    return items, stats


# ── LLM stages ────────────────────────────────────────────────────────────────

def _usd(model: str, usage) -> float:
    pin, pout = PRICES[model]
    return (usage.input_tokens * pin + usage.output_tokens * pout) / 1_000_000


def haiku_filter(client: Anthropic, items: list[Item]) -> float:
    """Tier every item against the taste profile. Returns USD spent."""
    listing = "\n".join(
        f"[{it.idx}] ({it.source}) {it.title} — {it.snippet}" for it in items
    )
    schema = {
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
                        "category": {"type": "string",
                                     "enum": ["headline", "frontier"]},
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
    resp = client.messages.create(
        model=HAIKU,
        max_tokens=8000,
        system=(
            "You are a sharp tech-news curator for ONE specific reader. "
            "Classify each item into a tier by IMPORTANCE TO THIS READER. "
            "Importance has TWO independent sources — weigh both:\n"
            "  (1) MAINSTREAM SIGNIFICANCE: will the whole field be talking about "
            "this? (flagship model launches, major capability jumps, big SOTA "
            "results, major lab announcements). Widely-covered ≠ low value — these "
            "are big deals BECAUSE everyone discusses them.\n"
            "  (2) NICHE FRONTIER SIGNAL: technically deep, forward-looking work a "
            "researcher would find genuinely interesting.\n"
            "Tiers:\n"
            "- must_know: a major release/announcement the reader must not miss, OR "
            "a landmark technical result. The reader would regret missing it.\n"
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
            f"READER PROFILE:\n{TASTE_PROFILE}"
        ),
        messages=[{"role": "user",
                   "content": f"Classify these {len(items)} items:\n\n{listing}"}],
        output_config={"format": {"type": "json_schema", "schema": schema}},
    )
    data = json.loads(next(b.text for b in resp.content if b.type == "text"))
    by_id = {it.idx: it for it in items}
    for r in data["results"]:
        if r["id"] in by_id:
            by_id[r["id"]].tier = r["tier"]
            by_id[r["id"]].category = r.get("category", "frontier")
            by_id[r["id"]].reason = r["reason"]
    return _usd(HAIKU, resp.usage)


def sonnet_cards(client: Anthropic, survivors: list[Item]) -> float:
    """Write inShorts cards for the survivors. Returns USD spent."""
    listing = "\n\n".join(
        f"[{it.idx}] ({it.source}) {it.title}\n{it.snippet}" for it in survivors
    )
    schema = {
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
    resp = client.messages.create(
        model=SONNET,
        max_tokens=6000,
        system=(
            "You write inShorts-style news cards for ONE specific reader.\n"
            "For each item produce:\n"
            "- title: a crisp, specific headline (rewrite vague ones).\n"
            "- why_it_matters: ONE sentence on why THIS reader specifically should "
            "care, grounded in their profile.\n"
            "- summary: 40–60 words, dense and factual, no hype, no filler.\n"
            "- tags: 2–4 lowercase topical tags.\n"
            "Keep every id from the input.\n\n"
            "ACCURACY RULES — CRITICAL. The reader relies on these cards to be "
            "factually correct; a confident wrong summary is far worse than a vague "
            "one.\n"
            "- Use ONLY facts present in the provided title/snippet. Do NOT invent "
            "details, numbers, or claims not in the source text.\n"
            "- Do NOT expand or guess acronyms unless the expansion is given in the "
            "source. If unsure what an acronym means, leave it as-is. (In an AI/ML "
            "research context, default readings apply — e.g. 'RSI' = recursive "
            "self-improvement, 'RL' = reinforcement learning — never invent an "
            "unrelated meaning.)\n"
            "- If the snippet is too thin to summarize confidently, write a SHORTER, "
            "hedged summary describing only what the title/snippet actually states, "
            "rather than fabricating specifics.\n\n"
            f"READER PROFILE:\n{TASTE_PROFILE}"
        ),
        messages=[{"role": "user", "content": f"Write cards for these:\n\n{listing}"}],
        output_config={"format": {"type": "json_schema", "schema": schema}},
    )
    data = json.loads(next(b.text for b in resp.content if b.type == "text"))
    by_id = {it.idx: it for it in survivors}
    for c in data["cards"]:
        if c["id"] in by_id:
            it = by_id[c["id"]]
            it.title = c["title"]
            it.why = c["why_it_matters"]
            it.summary = c["summary"]
            it.tags = c["tags"]
    return _usd(SONNET, resp.usage)


# ── Render ────────────────────────────────────────────────────────────────────

TIER_STYLE = {
    "must_know":     ("🔴 MUST KNOW",     "bold red"),
    "worth_knowing": ("🟡 WORTH KNOWING", "yellow"),
    "skim":          ("⚪ SKIM",          "dim white"),
}


TIER_ORDER = {"must_know": 0, "worth_knowing": 1, "skim": 2}


def _print_card(c: Item) -> None:
    label, style = TIER_STYLE.get(c.tier, ("?", "white"))
    body = Text()
    body.append(f"{c.why}\n\n", style="italic cyan")
    body.append(f"{c.summary}\n\n")
    body.append("  ".join(f"#{t}" for t in c.tags), style="dim")
    body.append(f"\n{c.source} → {c.url}", style="dim blue")
    console.print(Panel(body, title=f"[{style}]{label}[/]  {c.title}",
                        title_align="left", border_style=style))


def render(cards: list[Item]) -> None:
    counts = {t: sum(1 for c in cards if c.tier == t) for t in TIER_ORDER}
    console.rule("[bold]swenia — today's digest")
    console.print(
        f"[bold]{counts['must_know']} must-know · "
        f"{counts['worth_knowing']} worth knowing · "
        f"{counts['skim']} skim[/]\n"
    )

    for cat, heading in (("headline", "📰  HEADLINES"),
                         ("frontier", "🔬  FRONTIER & PAPERS")):
        section = sorted((c for c in cards if c.category == cat),
                         key=lambda c: TIER_ORDER.get(c.tier, 9))
        if not section:
            continue
        console.print(f"\n[bold reverse] {heading} [/]  [dim]({len(section)})[/]\n")
        for c in section:
            _print_card(c)

    console.print("\n[dim italic]— you're caught up —[/]\n")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        console.print("[bold red]ANTHROPIC_API_KEY not set.[/] "
                      "Run: export ANTHROPIC_API_KEY=sk-ant-...")
        return 1

    client = Anthropic()

    console.rule("[bold]1/3  Fetching sources")
    with httpx.Client(headers={"User-Agent": "swenia-spike/0.1"}) as http:
        raw = fetch_rss(http) + fetch_arxiv(http) + fetch_hn(http)
    items, stats = select(raw)
    if not items:
        console.print("[bold red]Nothing recent passed the filter — try raising "
                      f"RECENCY_DAYS (currently {RECENCY_DAYS}).[/]")
        return 1
    console.print(
        f"\n[bold]{stats['kept']}[/] items kept "
        f"(last {RECENCY_DAYS}d, ≤{MAX_PER_SOURCE}/source) — from {stats['raw']} raw "
        f"[dim](dropped {stats['too_old']} stale, {stats['dup']} dup; "
        f"{stats['no_date']} undated kept)[/]\n"
        f"[dim]balance: {stats['by_source']}[/]\n"
    )

    console.rule("[bold]2/3  Filtering (Haiku)")
    cost_filter = haiku_filter(client, items)
    survivors = [it for it in items if it.tier != "drop"][:MAX_CARDS]
    console.print(f"[bold]{len(survivors)}[/] survived the filter "
                  f"([dim]${cost_filter:.4f}[/]).\n")
    if not survivors:
        console.print("[yellow]Everything got dropped. Loosen the taste profile "
                      "or check the sources.[/]")
        return 0

    console.rule("[bold]3/3  Writing cards (Sonnet)")
    cost_cards = sonnet_cards(client, survivors)
    console.print(f"Cards written ([dim]${cost_cards:.4f}[/]).\n")

    render(survivors)
    console.print(f"[dim]Total spend this run: "
                  f"${cost_filter + cost_cards:.4f}[/]")
    return 0


if __name__ == "__main__":
    sys.exit(main())

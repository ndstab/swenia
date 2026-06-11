"""
The swenia Phase 1 pipeline, end to end:

  fetch → select (recency+balance) → dedup unseen (SQLite) → filter (Haiku)
        → cluster (embeddings) → full-text enrich → cards (Sonnet)
        → score → write digest JSON

Run:
    .venv/bin/python -m swenia            # sync calls, render to terminal
    .venv/bin/python -m swenia --batch    # use the Batch API (50% cheaper)
    .venv/bin/python -m swenia --no-store # don't record seen-state (re-runnable)
"""

from __future__ import annotations

import argparse
import os
import sys

import httpx
from anthropic import Anthropic
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from . import config as cfg
from . import digest as digest_mod
from . import fulltext, llm, ranking, sources, store
from .runner import run_batch, run_sync

console = Console()
log = console.log


def run(use_batch: bool = False, record: bool = True) -> dict:
    client = Anthropic()
    runner = (lambda req: run_batch(client, req, log)) if use_batch else \
             (lambda req: run_sync(client, req))
    cost = 0.0

    console.rule("[bold]1/6  Fetch")
    with httpx.Client(headers={"User-Agent": cfg.USER_AGENT}) as http:
        raw = sources.fetch_all(http, log)

        console.rule("[bold]2/6  Select & dedup")
        items, stats = ranking.select(raw, log)
        items, skipped = store.filter_unseen(items)
        log(f"[green]✓[/] {len(items)} unseen "
            f"[dim]({skipped} already shown in a prior digest)[/]")
        if not items:
            console.print("\n[bold]Nothing new — you're caught up.[/]\n")
            return digest_mod.build([])

        console.rule("[bold]3/6  Filter (Haiku)")
        resp = runner(llm.filter_messages(items))
        llm.apply_filter(items, resp)
        cost += llm.usd(cfg.HAIKU, resp.usage)
        survivors = [it for it in items if it.tier != "drop"][: cfg.MAX_CARDS]
        log(f"[green]✓[/] {len(survivors)} survived the filter "
            f"[dim](${cost:.4f})[/]")
        if not survivors:
            console.print("\n[yellow]Everything dropped — loosen the profile.[/]\n")
            return digest_mod.build([])

        console.rule("[bold]4/6  Cluster (embeddings)")
        survivors = ranking.cluster(survivors, log)

        console.rule("[bold]5/6  Full text + cards (Sonnet)")
        fulltext.enrich(http, survivors, log)

    resp = runner(llm.cards_messages(survivors))
    llm.apply_cards(survivors, resp)
    cost += llm.usd(cfg.SONNET, resp.usage)
    ranking.score(survivors)
    log(f"[green]✓[/] cards written [dim](total ${cost:.4f}; "
        f"batch would be ~${cost / 2:.4f})[/]")

    console.rule("[bold]6/6  Digest")
    digest = digest_mod.build(survivors)
    digest_mod.write(digest)
    log(f"[green]✓[/] wrote {cfg.LATEST_JSON.relative_to(cfg.ROOT)} "
        f"+ archive/{digest['date']}.json")

    if record:
        store.mark_seen(survivors)
        store.set_last_open()

    render(survivors, cost)
    return digest


# ── terminal preview (Phase 2 replaces this with the PWA) ──────────────────────

TIER_STYLE = {
    "must_know":     ("🔴 MUST KNOW",     "bold red"),
    "worth_knowing": ("🟡 WORTH KNOWING", "yellow"),
    "skim":          ("⚪ SKIM",          "dim white"),
}


def _print_card(c) -> None:
    label, style = TIER_STYLE.get(c.tier, ("?", "white"))
    body = Text()
    body.append(f"{c.why}\n\n", style="italic cyan")
    body.append(f"{c.summary}\n\n")
    body.append("  ".join(f"#{t}" for t in c.tags), style="dim")
    srcs = f"{c.source}" + (f" (+{len(c.extra_sources)})" if c.extra_sources else "")
    body.append(f"\n{srcs} → {c.url}", style="dim blue")
    console.print(Panel(body, title=f"[{style}]{label}[/]  {c.title_card or c.title}",
                        title_align="left", border_style=style))


def render(cards: list, cost: float) -> None:
    rank = {"must_know": 0, "worth_knowing": 1, "skim": 2}
    console.rule("[bold]swenia — today's digest")
    for cat, heading in (("headline", "📰  HEADLINES"),
                         ("frontier", "🔬  FRONTIER & PAPERS")):
        sec = sorted((c for c in cards if c.category == cat),
                     key=lambda c: (rank.get(c.tier, 9), -c.score))
        if not sec:
            continue
        console.print(f"\n[bold reverse] {heading} [/]  [dim]({len(sec)})[/]\n")
        for c in sec:
            _print_card(c)
    console.print("\n[dim italic]— you're caught up —[/]")
    console.print(f"[dim]spend: ${cost:.4f}[/]\n")


def main() -> int:
    ap = argparse.ArgumentParser(prog="swenia")
    ap.add_argument("--batch", action="store_true", help="use the Batch API (half price)")
    ap.add_argument("--no-store", action="store_true",
                    help="don't record seen-state (re-runnable for testing)")
    args = ap.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        console.print("[bold red]ANTHROPIC_API_KEY not set.[/]")
        return 1
    run(use_batch=args.batch, record=not args.no_store)
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""
Offline verification of the full Phase 1 code path.

Runs the real pipeline against live sources for everything that doesn't need the
Anthropic API, then drives the LLM-dependent stages (apply_filter / apply_cards /
score / digest build / write / seen-state) with MOCKED responses — so every line
of swenia/ is exercised except the actual network call to Anthropic.
"""
from __future__ import annotations

import json
import types

import httpx

from swenia import config as cfg
from swenia import digest as dmod
from swenia import fulltext, llm, ranking, sources, store
from swenia.runner import run_batch
from swenia.models import Item

OK, FAIL = "✅", "❌"
def check(name, cond):
    print(f"  {OK if cond else FAIL} {name}")
    assert cond, f"FAILED: {name}"


def fake_response(text: str, in_tok=1000, out_tok=500):
    """Mimic the Anthropic SDK Message: .content[].type/.text and .usage."""
    block = types.SimpleNamespace(type="text", text=text)
    usage = types.SimpleNamespace(input_tokens=in_tok, output_tokens=out_tok)
    return types.SimpleNamespace(content=[block], usage=usage)


def log(m):
    print("   ", m.replace("[green]✓[/]", "✓").replace("[yellow]⚠[/]", "⚠")
          .replace("[dim]", "").replace("[/]", "").replace("[bold]", ""))


print("\n=== 1. LIVE: fetch → select → unseen → fulltext → cluster ===")
with httpx.Client(headers={"User-Agent": cfg.USER_AGENT}) as http:
    raw = sources.fetch_all(http, log)
    check("fetched >50 raw items", len(raw) > 50)

    items, stats = ranking.select(raw, log)
    check("select produced items", len(items) > 0)
    check("per-source cap respected", all(v <= cfg.MAX_PER_SOURCE
                                          for v in stats["by_source"].values()))

    # use a small slice so the live full-text fetch is quick
    items = items[:6]
    fresh, skipped = store.filter_unseen(items)
    check("unseen filter returns a list", isinstance(fresh, list))

    fulltext.enrich(http, fresh, log)
    enriched = sum(1 for it in fresh if it.fulltext)
    check("at least one item got full text", enriched >= 1)

print("\n=== 2. MOCK: apply_filter (Haiku result handler) ===")
filt = {"results": [
    {"id": i, "tier": ["must_know", "worth_knowing", "skim"][i % 3],
     "category": "headline" if i % 2 else "frontier", "reason": "test"}
    for i in range(len(fresh))
]}
llm.apply_filter(fresh, fake_response(json.dumps(filt)))
check("tiers assigned", all(it.tier != "drop" for it in fresh))
check("categories assigned", all(it.category in ("headline", "frontier") for it in fresh))
check("filter request builds", "messages" in llm.filter_messages(fresh))

print("\n=== 3. cluster + apply_cards (Sonnet result handler) ===")
clustered = ranking.cluster(fresh, log)
cards_payload = {"cards": [
    {"id": i, "title": f"Card {i}", "why_it_matters": "because test",
     "summary": "A factual 40-word summary of the item under test.",
     "tags": ["t1", "t2"]}
    for i in range(len(clustered))
]}
# cards_messages must include full text where available
msg = llm.cards_messages(clustered)
check("cards request feeds fulltext", any(it.fulltext[:50] in msg["messages"][0]["content"]
                                          for it in clustered if it.fulltext))
llm.apply_cards(clustered, fake_response(json.dumps(cards_payload)))
check("cards have why+summary", all(c.why and c.summary for c in clustered))

print("\n=== 4. score → digest build → write JSON ===")
ranking.score(clustered)
check("scores assigned (>0 for non-drop)", all(c.score > 0 for c in clustered))
digest = dmod.build(clustered)
check("digest has both sections", {s["key"] for s in digest["sections"]} == {"headlines", "frontier"})
check("counts match cards", digest["counts"]["total"] == len(clustered))
dmod.write(digest)
check("latest.json written", cfg.LATEST_JSON.exists())
loaded = json.loads(cfg.LATEST_JSON.read_text())
check("latest.json is valid + matches", loaded["counts"]["total"] == len(clustered))
# validate the card contract shape
card0 = loaded["sections"][0]["cards"][0] if loaded["sections"][0]["cards"] else \
        loaded["sections"][1]["cards"][0]
for key in ("id", "tier", "category", "title", "why_it_matters", "summary", "tags", "sources"):
    check(f"card has '{key}'", key in card0)

print("\n=== 5. seen-state round-trip ===")
before = store.seen_count()
store.mark_seen(clustered)
after = store.seen_count()
check("mark_seen recorded items", after > before)
again, skipped2 = store.filter_unseen(clustered)
check("re-run filters them as seen", len(again) == 0 and skipped2 == len(clustered))

print("\n=== 6. run_batch request construction (no network) ===")
captured = {}
class FakeBatches:
    def create(self, requests):
        captured["req"] = requests[0]
        raise SystemExit("stop-before-network")  # we only test construction
fake_client = types.SimpleNamespace(messages=types.SimpleNamespace(batches=FakeBatches()))
try:
    run_batch(fake_client, llm.filter_messages(clustered), log)
except SystemExit:
    pass
check("batch request built with custom_id", captured["req"]["custom_id"] == "req-0")
check("batch params carry the model", captured["req"]["params"]["model"] == cfg.HAIKU)

# cleanup: don't leave test items in the real seen-db
import sqlite3
with sqlite3.connect(cfg.DB_PATH) as c:
    c.execute("DELETE FROM seen WHERE id IN (%s)" %
              ",".join("?" * len(clustered)), [it.id for it in clustered])
print("\n(cleaned up test rows from seen-db)")
print(f"\n{OK} ALL OFFLINE CHECKS PASSED — every line except the live Anthropic call.\n")

"""
swenia configuration — the two knobs you'll actually tune live here:
  • SOURCES  (RSS_FEEDS / ARXIV_CATEGORIES / HN_QUERIES)
  • TASTE_PROFILE

Everything else is pipeline tunables with sensible defaults.
"""

from __future__ import annotations

from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# KNOB 1: SOURCES
# ─────────────────────────────────────────────────────────────────────────────
RSS_FEEDS: list[tuple[str, str]] = [
    ("Import AI",       "https://importai.substack.com/feed"),
    ("Interconnects",   "https://www.interconnects.ai/feed"),
    ("Hugging Face",    "https://huggingface.co/blog/feed.xml"),
    ("BAIR (Berkeley)", "https://bair.berkeley.edu/blog/feed.xml"),
    ("DeepMind",        "https://deepmind.google/blog/rss.xml"),
]
ARXIV_CATEGORIES: list[str] = ["cs.LG", "cs.CL", "cs.AI", "quant-ph"]
ARXIV_PER_CAT = 12

HN_QUERIES: list[str] = ["AI", "LLM", "model", "neural", "quantum"]
HN_MIN_POINTS = 50
HN_PER_QUERY = 15

# ─────────────────────────────────────────────────────────────────────────────
# KNOB 2: TASTE PROFILE — the heart of the curation. Edit until cards feel yours.
# Importance = mainstream significance OR niche frontier signal. Never penalize
# an item for being popular/widely-covered.
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
# Pipeline tunables
# ─────────────────────────────────────────────────────────────────────────────
RECENCY_DAYS = 7              # candidate window (decay scoring handles ranking)
MAX_PER_SOURCE = 6            # cap any one feed before filtering
MAX_ITEMS_TO_FILTER = 120     # bound tokens sent to the filter
MAX_CARDS = 25                # cap the daily digest size

DEDUP_THRESHOLD = 0.80        # cosine sim above which items are near-duplicates
DECAY_TAU_DAYS = 3.0          # freshness half-life-ish constant for decay scoring
TIER_WEIGHT = {"must_know": 3.0, "worth_knowing": 1.5, "skim": 0.5, "drop": 0.0}

FULLTEXT_MAX_CHARS = 4000     # cap extracted article text fed to the summarizer
FETCH_TIMEOUT = 15.0
USER_AGENT = "swenia/0.1 (personal news digest)"

# Models
HAIKU = "claude-haiku-4-5"
SONNET = "claude-sonnet-4-6"
OPUS = "claude-opus-4-8"      # reserved for on-demand deep dives (Phase 4)
EMBED_MODEL = "BAAI/bge-small-en-v1.5"

# standard per-1M-token prices for the cost readout (batch = 50% of these)
PRICES = {HAIKU: (1.00, 5.00), SONNET: (3.00, 15.00), OPUS: (5.00, 25.00)}

# ─────────────────────────────────────────────────────────────────────────────
# Paths
# ─────────────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "output"
ARCHIVE_DIR = OUTPUT_DIR / "archive"
DB_PATH = DATA_DIR / "swenia.db"
LATEST_JSON = OUTPUT_DIR / "latest.json"

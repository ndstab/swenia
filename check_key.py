#!/usr/bin/env python3
"""Diagnose the ANTHROPIC_API_KEY without leaking it. Run: .venv/bin/python check_key.py"""
import os
from anthropic import Anthropic

k = os.environ.get("ANTHROPIC_API_KEY")
if not k:
    print("✗ ANTHROPIC_API_KEY is not set in this shell.")
    raise SystemExit(1)

# Safe metadata only — never prints the secret middle.
print(f"length            : {len(k)}")
print(f"prefix (first 13) : {k[:13]!r}")
print(f"last 4            : …{k[-4:]!r}")
print(f"leading whitespace: {k != k.lstrip()}")
print(f"trailing newline  : {k != k.rstrip()}")
print(f"surrounding quotes: {k[:1] in chr(34)+chr(39) or k[-1:] in chr(34)+chr(39)}")

kind = ("OAuth token (needs Bearer auth, NOT usable as x-api-key)"
        if k.startswith("sk-ant-oat") else
        "API key (correct type)" if k.startswith("sk-ant-api") else
        "UNKNOWN prefix — likely not a valid Anthropic key")
print(f"key type          : {kind}")

print("\nMaking a 1-token test call…")
try:
    r = Anthropic().messages.create(
        model="claude-haiku-4-5", max_tokens=1,
        messages=[{"role": "user", "content": "hi"}],
    )
    print(f"✓ Key works. (request_id {r._request_id})")
except Exception as e:  # noqa: BLE001
    print(f"✗ {type(e).__name__}: {e}")

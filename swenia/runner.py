"""
Two ways to run an LLM stage:

  run_sync()  — a normal messages.create call. Fast feedback for local dev.
  run_batch() — the Messages Batch API (flat 50% off). Used in production where
                the once-daily job isn't latency-sensitive.

Both take a request dict (from llm.*_messages()) and return the response object,
so the caller's apply_*() handler works identically either way.
"""

from __future__ import annotations

import time

from anthropic import Anthropic
from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
from anthropic.types.messages.batch_create_params import Request


def run_sync(client: Anthropic, req: dict):
    return client.messages.create(**req)


def run_batch(client: Anthropic, req: dict, log, poll_s: int = 15):
    """Submit a single-request batch and block until it completes.

    A daily digest has only 2 LLM calls, so one item per batch is fine; the
    point is the 50% price, not parallelism. Returns the same message object
    shape as run_sync so apply_*() handlers are reused unchanged.
    """
    batch = client.messages.batches.create(requests=[
        Request(custom_id="req-0",
                params=MessageCreateParamsNonStreaming(**req))
    ])
    log(f"[dim]batch {batch.id} submitted ({req['model']})…[/]")
    while True:
        b = client.messages.batches.retrieve(batch.id)
        if b.processing_status == "ended":
            break
        time.sleep(poll_s)
    for result in client.messages.batches.results(batch.id):
        if result.result.type == "succeeded":
            return result.result.message
        raise RuntimeError(f"batch request failed: {result.result.type}")
    raise RuntimeError("batch returned no results")

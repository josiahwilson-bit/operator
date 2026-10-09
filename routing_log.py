#!/usr/bin/env python3
"""
Structured routing log for operator.

Every routing decision is recorded with full context:
  signal, candidate teams, eligibility per team, margin scores,
  winner, runner-up, timestamp.

This is the accuracy layer: you can audit WHY a signal went where
it did, not just where it went. JSONL — one decision per line,
append-only, machine-readable.

Used by agentic_runner.py; readable by finance_summary.py.
"""
import json
import os
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
RUN = os.path.join(HERE, "run_state")
ROUTING_LOG = os.path.join(RUN, "routing_log.jsonl")


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log_routing(signal, classification, candidates, assignment):
    """Log one routing decision with full context.

    candidates: list of {team_id, eligible, margin, reason}
    assignment: team_id that won (or None)
    """
    ranked = sorted(candidates, key=lambda c: c["margin"], reverse=True)
    entry = {
        "ts": _now(),
        "signal_id": signal["id"],
        "source": signal["source"],
        "classification": classification,
        "candidates": candidates,
        "ranked": [c["team_id"] for c in ranked if c["eligible"]],
        "winner": assignment,
        "runner_up": next((c["team_id"] for c in ranked
                           if c["eligible"] and c["team_id"] != assignment),
                          None),
        "ineligible": [c["team_id"] for c in candidates
                       if not c["eligible"]],
    }
    with open(RUN + "/routing_log.jsonl", "a") as f:
        f.write(json.dumps(entry) + "\n")
    return entry


def read_log():
    if not os.path.exists(ROUTING_LOG):
        return []
    with open(ROUTING_LOG) as f:
        return [json.loads(line) for line in f if line.strip()]

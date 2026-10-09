#!/usr/bin/env python3
"""
Contract store: persists contracts between runs so approval is a
separate human action, not a function call inside the runner.

Contracts live in run_state/contracts.json. The runner creates them
(proposed/disputed); approve.py moves them (approved). Neither process
can do the other's job.
"""
import json
import os
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
RUN = os.path.join(HERE, "run_state")
STORE = os.path.join(RUN, "contracts.json")


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load():
    if not os.path.exists(STORE):
        return {}
    with open(STORE) as f:
        return json.load(f)


def save(contracts):
    tmp = STORE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(contracts, f, indent=2)
    os.replace(tmp, STORE)  # atomic write


def upsert(contract):
    """Persist a Contract object (from agentic_runner)."""
    contracts = load()
    contracts[contract.id] = {
        "id": contract.id,
        "signal_id": contract.signal_id,
        "team_id": contract.team_id,
        "scope": contract.scope,
        "budget": contract.budget,
        "urgency": contract.urgency,
        "state": contract.state,
        "history": [{"state": s, "note": n, "ts": _now()}
                    for s, n in contract.history],
        "deadline": getattr(contract, "deadline", None),
        "updated": _now(),
    }
    save(contracts)
    return contract.id


def pending():
    """Contracts awaiting human decision (proposed or disputed)."""
    return {cid: c for cid, c in load().items()
            if c["state"] in ("proposed", "disputed")}

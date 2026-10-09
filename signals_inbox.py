#!/usr/bin/env python3
"""
signals_inbox.py — the input edge of operator.

Drop JSON signal files into run_state/inbox/. The next pipeline run
picks them up, processes them, and moves them to run_state/inbox/processed/.

Signal file format (SIG-*.json):
  {"id": "SIG-005", "source": "manual",
   "content": "what happened, in plain words",
   "kind": "inbound_lead | opportunity | noise",
   "amount": 0}

"sources" can be anything: manual, mastodon, reddit, webhook, email.
"kinds" drive classification: inbound_lead (high), opportunity (normal),
anything else is noise (filtered, still logged).

Pre-auth pattern: the inbox works the day it's built. Real sources fill
it whenever they're ready. Empty inbox -> pipeline falls back to synthetic
signals so demos and tests keep working.
"""
import glob
import json
import os
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
RUN = os.path.join(HERE, "run_state")
INBOX = os.path.join(RUN, "inbox")
PROCESSED = os.path.join(INBOX, "processed")

REQUIRED = ("id", "source", "content")
VALID_KINDS = ("inbound_lead", "opportunity", "noise")


def ensure():
    os.makedirs(PROCESSED, exist_ok=True)


def read_inbox():
    """Return (valid_signals, rejected_files). Validates every file."""
    ensure()
    valid, rejected = [], []
    for path in sorted(glob.glob(os.path.join(INBOX, "SIG-*.json"))):
        name = os.path.basename(path)
        try:
            with open(path) as f:
                sig = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            rejected.append((name, f"unreadable: {e}"))
            continue
        missing = [k for k in REQUIRED if k not in sig]
        if missing:
            rejected.append((name, f"missing fields: {missing}"))
            continue
        sig.setdefault("kind", "noise")
        sig.setdefault("amount", 0)
        if sig["kind"] not in VALID_KINDS:
            rejected.append(
                (name, f"kind must be one of {VALID_KINDS}"))
            continue
        sig["_inbox_file"] = name
        valid.append(sig)
    return valid, rejected


def archive(signals):
    """Move processed signal files to processed/. Idempotent."""
    for sig in signals:
        src = os.path.join(INBOX, sig["_inbox_file"])
        dst = os.path.join(PROCESSED, sig["_inbox_file"])
        if os.path.exists(src):
            shutil.move(src, dst)


def example():
    """Write an example signal file (for documentation/testing)."""
    ensure()
    path = os.path.join(INBOX, "SIG-EXAMPLE.json")
    if os.path.exists(path):
        return path
    with open(path, "w") as f:
        json.dump({
            "id": "SIG-EXAMPLE",
            "source": "manual",
            "content": "Example: replace this file with a real signal, "
                       "or delete it.",
            "kind": "noise",
            "amount": 0,
        }, f, indent=2)
    return path

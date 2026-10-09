#!/usr/bin/env python3
"""
spec_sync_node.py — drift detector between enforced policy and its documents.

Compares:
  SOURCE OF TRUTH: gate.py ACTION_GATES + GATE_POLICIES (enforced)
  DOCUMENT:        rego-policy-mock.rego action_gates + gate_authority (review)

On drift: publishes a finding (findings.log + notify) describing exactly
what disagrees. Idempotent: drift is reported once per change, silent
until either side moves again.

Same node pattern: read, compare, publish, idempotent. Stdlib only.
"""
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
RUN = os.path.join(HERE, "run_state")
os.makedirs(RUN, exist_ok=True)
sys.path.insert(0, os.path.join(HERE, "..", "coordinator-a"))
sys.path.insert(0, os.path.join(HERE, "..", "github-runner"))

REGO_PATH = os.path.join(
    HERE, "..", "..", "research", "agentic-routing-20261009",
    "rego-policy-mock.rego")
POS_PATH = os.path.join(RUN, "spec_sync.pos")
FINDINGS = os.path.join(RUN, "findings.log")


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()[:16]


def live_policy():
    """Source of truth: import gate.py, read the actual policy data."""
    from gate import ApprovalGate
    return {
        "action_gates": dict(ApprovalGate.ACTION_GATES),
        "authority": {g: p["authority"]
                      for g, p in ApprovalGate.GATE_POLICIES.items()},
    }


def parse_rego(path):
    """Parse the mockup's action_gates and gate_authority maps."""
    with open(path) as f:
        text = f.read()

    def parse_map(name):
        m = re.search(rf"^{name}\s*:=\s*\{{(.*?)\n\}}",
                      text, re.M | re.S)
        if not m:
            return {}
        out = {}
        for line in m.group(1).splitlines():
            line = line.strip().rstrip(",")
            if not line or line.startswith("#"):
                continue
            kv = re.match(r'"([^"]+)"\s*:\s*(.*)', line)
            if not kv:
                continue
            key, val = kv.group(1), kv.group(2).strip()
            if val.startswith("["):
                out[key] = re.findall(r'"([^"]+)"', val)
            else:
                vm = re.match(r'"([^"]+)"', val)
                out[key] = vm.group(1) if vm else val
        return out

    rate = re.search(r"rate_limit_per_hour\s*:=\s*(\d+)", text)
    return {
        "action_gates": parse_map("action_gates"),
        "authority": parse_map("gate_authority"),
        "rate_limit": int(rate.group(1)) if rate else None,
    }


def diff(live, doc):
    """Return list of drift descriptions (empty = in sync)."""
    drifts = []
    for action, gates in live["action_gates"].items():
        if action not in doc["action_gates"]:
            drifts.append(f"action '{action}' missing from rego mockup")
        elif sorted(doc["action_gates"][action]) != sorted(gates):
            drifts.append(
                f"action '{action}': live={sorted(gates)} "
                f"rego={sorted(doc['action_gates'][action])}")
    for action in doc["action_gates"]:
        if action not in live["action_gates"]:
            drifts.append(f"action '{action}' in rego but not in live policy")
    for gate, auth in live["authority"].items():
        if gate not in doc["authority"]:
            drifts.append(f"gate '{gate}' authority missing from rego mockup")
        elif doc["authority"][gate] != auth:
            drifts.append(f"gate '{gate}': live authority='{auth}' "
                          f"rego='{doc['authority'][gate]}'")
    return drifts


def publish_finding(drifts):
    from discord_notify import send as notify
    detail = "; ".join(drifts)
    line = (f"[{_now()}] SPEC-SYNC decision=DRIFT team=operator :: "
            f"policy drift: {detail}\n")
    with open(FINDINGS, "a") as f:
        f.write(line)
    notify(f"operator spec drift: {detail}")
    return line


def main():
    gate_path = os.path.join(HERE, "..", "coordinator-a", "gate.py")
    gate_hash, rego_hash = sha(gate_path), sha(REGO_PATH)

    pos = {}
    if os.path.exists(POS_PATH):
        with open(POS_PATH) as f:
            pos = json.load(f)

    # Idempotent: both sides unchanged since last check -> silent.
    if (pos.get("gate_hash") == gate_hash
            and pos.get("rego_hash") == rego_hash):
        print("spec-sync: no changes since last check, silent.")
        return

    live = live_policy()
    doc = parse_rego(REGO_PATH)
    drifts = diff(live, doc)

    if drifts:
        line = publish_finding(drifts)
        print(f"spec-sync: DRIFT published ({len(drifts)} item(s))")
        print(" ", line.strip()[:160])
        pos["last_drift"] = hashlib.sha256(
            "\n".join(sorted(drifts)).encode()).hexdigest()[:16]
    else:
        print("spec-sync: live policy and rego mockup agree. no drift.")

    pos.update({"gate_hash": gate_hash, "rego_hash": rego_hash,
                "checked": _now()})
    with open(POS_PATH, "w") as f:
        json.dump(pos, f, indent=2)


if __name__ == "__main__":
    main()

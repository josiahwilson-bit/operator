#!/usr/bin/env python3
"""
Notify node: watches the agentic runner's audit log and publishes a
finding per NEW decision record.

- Tails run_state/audit.jsonl; tracks position in run_state/notify_node.pos
- Publish = discord_notify.send() (no-op without DISCORD_WEBHOOK_URL —
  correct pre-auth behavior) AND append to run_state/findings.log
- Finding: timestamp | contract/task id | decision | team/tier | one-line reason
- Idempotent: re-running with no new records publishes nothing.

$0. Local only. No external sends beyond the pre-auth no-op notifier.
"""
import json
import os
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
RUN_STATE = os.path.join(HERE, "run_state")
AUDIT_LOG = os.path.join(RUN_STATE, "audit.jsonl")
POS_FILE = os.path.join(RUN_STATE, "notify_node.pos")
FINDINGS_LOG = os.path.join(RUN_STATE, "findings.log")

sys.path.insert(0, os.path.join(HERE, "..", "github-runner"))
from discord_notify import send as notify  # noqa: E402


def _read_pos():
    try:
        with open(POS_FILE) as f:
            return int(f.read().strip())
    except (FileNotFoundError, ValueError):
        return 0


def _write_pos(n):
    with open(POS_FILE, "w") as f:
        f.write(str(n))


def _parse_team(task_state):
    """team= is emitted by future runner versions; tier= exists today."""
    if not task_state:
        return "n/a"
    for part in str(task_state).split():
        if part.startswith("team="):
            return part.split("=", 1)[1]
        if part.startswith("tier="):
            return f"tier:{part.split('=', 1)[1]}"
    return "n/a"


def finding_for(record):
    meta = record.get("meta", {}) or {}
    reasons = meta.get("reasons") or []
    reason = reasons[0] if reasons else record.get("result", "?")
    # keep it to one line
    reason = " ".join(str(reason).split())[:160]
    team = _parse_team((meta.get("inputs_considered") or {})
                       .get("task_state_at_decision"))
    return {
        "ts": record.get("ts", ""),
        "contract": record.get("target", meta.get("task_id", "?")),
        "decision": (meta.get("decision") or record.get("result", "?")).upper(),
        "team": team,
        "reason": reason,
    }


def format_finding(f):
    return (f"[{f['ts']}] {f['contract']} decision={f['decision']} "
            f"team={f['team']} :: {f['reason']}")


def run():
    if not os.path.exists(AUDIT_LOG):
        print("no audit log yet — nothing to publish")
        return 0
    with open(AUDIT_LOG) as f:
        lines = f.readlines()
    pos = _read_pos()
    new_lines = lines[pos:]
    published = 0
    with open(FINDINGS_LOG, "a") as flog:
        for line in new_lines:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            # only decision records become findings
            if not str(record.get("action", "")).startswith("decision/"):
                continue
            f = finding_for(record)
            text = format_finding(f)
            notify(f"Agentic runner finding: {text}")
            flog.write(text + "\n")
            published += 1
    _write_pos(len(lines))
    print(f"notify node: {published} new finding(s) published, "
          f"position now {len(lines)}")
    return published


if __name__ == "__main__":
    n = run()
    sys.exit(0)

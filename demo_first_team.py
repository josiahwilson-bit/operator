#!/usr/bin/env python3
"""
First-team capture demo: proves the FULL contract lifecycle works,
not just the fail-closed refuse path.

Simulates the owner clearing one gate (actor="owner" — the only
authority the gate accepts), then re-runs that contract through
to verified. All synthetic. $0. No external effects.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from agentic_runner import (  # noqa: E402
    TEAMS, SIGNALS, classify_signal, TeamAdapter, Contract,
    run as pipeline_run,
)
from gate import ApprovalGate  # noqa: E402
from audit import AuditLog  # noqa: E402
from decision_records import emit_decision_record  # noqa: E402
from matching import solve_exact, flag_for_review  # noqa: E402

WORKDIR = os.path.join(HERE, "run_state")
os.makedirs(WORKDIR, exist_ok=True)


def main():
    print("== first-team capture demo ==\n")

    # --- stage 1: capture a real-shaped signal, classify it
    sig = {"id": "SIG-DEMO", "source": "mastodon",
           "content": ("Independent bookstore owner sent a 12-page vendor "
                       "agreement, unsure about the auto-renewal clause"),
           "kind": "inbound_lead", "amount": 295}
    c = classify_signal(sig)
    print(f"CAPTURED: {sig['id']} [{sig['source']}]")
    print(f"CLASSIFIED: type={c['type']} urgency={c['urgency']}")

    # --- stage 2: route to a team via the adapter + matching
    contractors = [TeamAdapter.team_to_contractor(t) for t in TEAMS]
    opp = TeamAdapter.signal_to_opportunity(sig, c)
    _, assignment = solve_exact([opp], contractors)
    team_id = assignment.get(sig["id"])
    print(f"ROUTED: {sig['id']} -> {team_id}")
    assert team_id, "no team captured the signal!"

    team = next(t for t in TEAMS if t["id"] == team_id)
    print(f"TEAM: {team_id} (framework={team['framework']} tier={team['tier']})")

    # --- stage 3: contract proposed, gate refuses (fail-closed, as before)
    gate = ApprovalGate(os.path.join(WORKDIR, "gates.db"))
    audit = AuditLog(os.path.join(WORKDIR, "audit.jsonl"))
    ctr = Contract(sig, team_id, c)
    gate.request_action(ctr.id, "execute",
                        summary=f"delegate {sig['id']} to {team_id}")
    ok, reasons = gate.check_action(ctr.id, "execute")
    emit_decision_record(gate, audit, ctr.id, "execute", ok, reasons,
                         task_state=f"contract={ctr.id} tier={team['tier']}",
                         gate_db_path=os.path.join(WORKDIR, "gates.db"))
    print(f"GATE (before approval): allow={ok} reasons={reasons}")
    assert not ok, "gate should refuse without owner approval"

    # --- stage 4: owner approves (the human step — simulated here)
    gate.approve_action(ctr.id, "execute", "owner")
    ok2, reasons2 = gate.check_action(ctr.id, "execute")
    emit_decision_record(gate, audit, ctr.id, "execute", ok2, reasons2,
                         task_state=f"contract={ctr.id} tier={team['tier']}",
                         gate_db_path=os.path.join(WORKDIR, "gates.db"),
                         actor_role="owner")
    print(f"GATE (after owner approval): allow={ok2} reasons={reasons2}")
    assert ok2, "gate should allow after owner approval"

    # --- stage 5: contract flows to verified
    ctr.transition("approved", "owner cleared the gate")
    ctr.transition("executing", f"team {team_id} started (synthetic)")
    ctr.transition("evidence_submitted", "synthetic evidence attached")
    ctr.transition("verified", "evidence accepted")
    print(f"CONTRACT: {ctr}")
    print("lifecycle:", " -> ".join(s for s, _ in ctr.history))

    # --- stage 6: chain integrity + full pipeline sanity
    chain = audit.verify_chain()
    print(f"\naudit chain valid: {chain[0]} ({chain[2]} records)")
    report, chain_ok = pipeline_run()
    print(f"full pipeline re-run: {len(report['contracts'])} contracts, "
          f"chain ok={chain_ok}")

    print("\nDEMO COMPLETE: first team captured, full lifecycle verified.")
    print("States proven: proposed -> approved -> executing -> "
          "evidence_submitted -> verified (plus the refuse->disputed path).")


if __name__ == "__main__":
    main()

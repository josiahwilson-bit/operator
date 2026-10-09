#!/usr/bin/env python3
"""
approve.py — the human interface to operator's gates.

This is the ONLY legitimate path to approve a contract. It requires:
  1. The contract to exist in pending state (proposed/disputed)
  2. The human to type the contract ID (no bulk approve, no --yes flag)
  3. Explicit confirmation with the contract's full details shown

Usage:
  python3 approve.py            # list pending contracts
  python3 approve.py CTR-001    # review + approve one contract

There is deliberately no non-interactive mode. Approval is a human
action; scripting it defeats the purpose.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from contract_store import load, save, pending  # noqa: E402

sys.path.insert(0, os.path.join(HERE, "..", "coordinator-a"))
from gate import ApprovalGate  # noqa: E402
from audit import AuditLog  # noqa: E402
from decision_records import emit_decision_record  # noqa: E402

RUN = os.path.join(HERE, "run_state")


def show(c):
    print(f"\n{c['id']} [{c['state']}]")
    print(f"  signal:  {c['signal_id']}")
    print(f"  team:    {c['team_id']}")
    print(f"  scope:   {c['scope']}")
    print(f"  budget:  ${c['budget']:.2f}")
    print(f"  urgency: {c['urgency']}")
    if c.get("deadline"):
        print(f"  deadline:{c['deadline']}")
    print("  history:")
    for h in c["history"]:
        print(f"    - {h['state']}: {h['note']}")


def main():
    args = sys.argv[1:]
    pend = pending()

    if not args:
        if not pend:
            print("no contracts pending human decision.")
            return
        print(f"{len(pend)} contract(s) pending:")
        for cid, c in pend.items():
            print(f"  {cid} [{c['state']}] {c['signal_id']} -> {c['team_id']}")
        print("\nrun: python3 approve.py <CONTRACT-ID> to review one")
        return

    cid = args[0].upper()
    if cid not in pend:
        print(f"{cid} is not pending (unknown, or already decided).")
        print("approval is only possible from proposed/disputed state.")
        return

    c = pend[cid]
    show(c)

    # The human must retype the ID — no accidental approvals.
    confirm = input(f"\ntype {cid} to approve, anything else to abort: ").strip()
    if confirm != cid:
        print("aborted. no changes made.")
        return

    # Clear the gate as owner, record the decision.
    gate = ApprovalGate(os.path.join(RUN, "gates.db"))
    audit = AuditLog(os.path.join(RUN, "audit.jsonl"))
    gate.approve_action(cid, "execute", "owner")
    ok, reasons = gate.check_action(cid, "execute")
    emit_decision_record(gate, audit, cid, "execute", ok, reasons,
                         task_state=f"contract={cid} approved-by=owner-cli",
                         gate_db_path=os.path.join(RUN, "gates.db"),
                         actor_role="owner")

    # Advance the contract.
    contracts = load()
    contracts[cid]["state"] = "approved"
    contracts[cid]["history"].append(
        {"state": "approved", "note": "owner approved via approve.py",
         "ts": contracts[cid]["updated"]})
    save(contracts)

    print(f"\n{cid} approved. gate={'clear' if ok else 'STILL BLOCKED: ' + str(reasons)}")
    if not ok:
        print("warning: gate still refuses — contract approved but cannot execute.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Agentic team routing runner — synthetic-only prototype.

Pipeline: CAPTURE -> CLASSIFY -> ROUTE -> DELEGATE -> GATE -> CONTRACT -> HUMAN REVIEW

Wires the real components (not stubs):
  - FinancialClassifier (github-runner/financial_logic.py) for money events
  - matching.solve_exact (coordinator-a) for signal->team assignment
  - ApprovalGate (coordinator-a/gate.py) for delegation authority
  - emit_decision_record (coordinator-a/decision_records.py) for audit
  - AuditLog (coordinator-a/audit.py) hash-chained log
  - discord_notify (github-runner) for human-review alerts (no-op without URL)

Troubleshooting notes (design gaps this runner closes):
  1. matching.py assigns opportunities->contractors by skills/capacity, NOT
     signals->teams. The TeamAdapter below translates explicitly.
  2. decision_records needs a real AuditLog (audit.py) — wired here.
  3. Gate "execute" action must be requested before check_action.
  4. Contract lifecycle did not exist anywhere — implemented here.
  5. Non-financial signal classification did not exist — implemented here.

All data synthetic. $0. No external effects. Exit 0 = pipeline healthy.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "coordinator-a"))
sys.path.insert(0, os.path.join(HERE, "..", "github-runner"))

from matching import solve_exact, flag_for_review          # noqa: E402
from gate import ApprovalGate                              # noqa: E402
from audit import AuditLog                                 # noqa: E402
from decision_records import emit_decision_record          # noqa: E402
from financial_logic import FinancialClassifier            # noqa: E402
from discord_notify import send as notify                  # noqa: E402

WORKDIR = os.path.join(HERE, "run_state")
os.makedirs(WORKDIR, exist_ok=True)

# ---------------------------------------------------------------- team registry
# Trust tiers: synthetic -> sandbox -> approved. New teams enter at synthetic.
TEAMS = [
    {"id": "research-crew", "framework": "smolagents",
     "capabilities": ["web", "data"], "slots": 8, "tier": "synthetic"},
    {"id": "notify-relay", "framework": "discord_notify",
     "capabilities": ["data"], "slots": 4, "tier": "sandbox"},
    {"id": "finance-watch", "framework": "financial_logic",
     "capabilities": ["data", "qa"], "slots": 4, "tier": "sandbox"},
]

# ---------------------------------------------------------------- capture (synthetic signals)
SIGNALS = [
    {"id": "SIG-001", "source": "mastodon",
     "content": "Small bakery owner asking about unfair delivery-app contract terms",
     "kind": "inbound_lead", "amount": 295},
    {"id": "SIG-002", "source": "reddit",
     "content": "r/smallbusiness thread: LLC annual fee confusion in California",
     "kind": "opportunity", "amount": 0},
    {"id": "SIG-003", "source": "webhook",
     "content": "Grant finalist notice pattern matched for LISC watch",
     "kind": "opportunity", "amount": 0},
    {"id": "SIG-004", "source": "mastodon",
     "content": "Unrelated meme repost with no business content",
     "kind": "noise", "amount": 0},
]

# ---------------------------------------------------------------- classify
def classify_signal(sig):
    """Signal classifier: same {type, urgency} shape as FinancialClassifier."""
    kind = sig.get("kind", "noise")
    urgency = "low"
    if kind == "inbound_lead":
        urgency = "high"
    elif kind == "opportunity":
        urgency = "normal"
    return {"type": kind, "urgency": urgency,
            "routable": kind in ("inbound_lead", "opportunity")}


class TeamAdapter:
    """Translates teams/signals into matching.py's contractor/opportunity
    schema. Explicit about the mapping so the abstraction doesn't leak."""

    @staticmethod
    def team_to_contractor(team):
        return {"id": team["id"], "skills": team["capabilities"],
                "capacity_hours": team["slots"]}

    @staticmethod
    def signal_to_opportunity(sig, classification):
        urgency_value = {"low": 100, "normal": 300, "high": 600,
                         "critical": 1000}[classification["urgency"]]
        return {"id": sig["id"],
                "margin": float(urgency_value + (sig.get("amount") or 0)),
                "hours": 2,
                "skills": ["web"] if sig["source"] in ("mastodon", "reddit")
                else ["data"]}


# ---------------------------------------------------------------- contract lifecycle
CONTRACT_STATES = ("proposed", "approved", "executing",
                   "evidence_submitted", "verified", "disputed")

class Contract:
    _n = 0

    def __init__(self, signal, team_id, classification):
        Contract._n += 1
        self.id = f"CTR-{Contract._n:03d}"
        self.signal_id = signal["id"]
        self.team_id = team_id
        self.scope = signal["content"][:120]
        self.budget = 0.0
        self.urgency = classification["urgency"]
        self.state = "proposed"
        self.history = [("proposed", "contract created from routed signal")]

    def transition(self, to, note=""):
        assert to in CONTRACT_STATES, f"unknown state {to}"
        self.history.append((to, note))
        self.state = to

    def __repr__(self):
        return (f"{self.id} [{self.state}] {self.signal_id} -> "
                f"{self.team_id} (${self.budget:.2f})")


# ---------------------------------------------------------------- pipeline
def run():
    fin = FinancialClassifier()
    gate = ApprovalGate(os.path.join(WORKDIR, "gates.db"))
    audit = AuditLog(os.path.join(WORKDIR, "audit.jsonl"))
    report = {"routed": [], "contracts": [], "disputed": [], "noise": []}

    # 1. CAPTURE + 2. CLASSIFY
    routable, classified = [], {}
    for sig in SIGNALS:
        c = classify_signal(sig)
        classified[sig["id"]] = c
        # Money events also run through the financial classifier
        if sig.get("amount"):
            fc = fin.classify({"kind": "payment", "status": "pending",
                               "amount": sig["amount"], "due_date": None})
            c["financial"] = fc["type"]  # unverified_payment until settled
        if c["routable"]:
            routable.append(sig)
        else:
            report["noise"].append(sig["id"])

    # 3. ROUTE via matching.py (through the adapter)
    contractors = [TeamAdapter.team_to_contractor(t) for t in TEAMS]
    opportunities = [TeamAdapter.signal_to_opportunity(s, classified[s["id"]])
                     for s in routable]
    _, assignment = solve_exact(opportunities, contractors)
    flagged = {oid: status for oid, _, _, status
               in flag_for_review(assignment, opportunities)}

    # 4. DELEGATE -> 5. GATE -> 6. CONTRACT
    for sig in routable:
        team_id = assignment.get(sig["id"])
        if not team_id:
            continue  # no eligible team: left unassigned, no contract
        team = next(t for t in TEAMS if t["id"] == team_id)
        ctr = Contract(sig, team_id, classified[sig["id"]])

        task_id = ctr.id
        gate.request_action(task_id, "execute",
                            summary=f"delegate {sig['id']} to {team_id}")
        # Synthetic tier: never auto-clear. Sandbox tier: still needs owner.
        # Nothing here clears gates — owner approval is the only path.
        ok, reasons = gate.check_action(task_id, "execute")
        emit_decision_record(gate, audit, task_id, "execute", ok, reasons,
                             task_state=f"contract={ctr.id} tier={team['tier']}",
                             gate_db_path=os.path.join(WORKDIR, "gates.db"))

        if ok:
            ctr.transition("approved", "gate cleared")
            ctr.transition("executing", f"team {team_id} started (synthetic)")
            # Synthetic execution: team returns evidence immediately
            ctr.transition("evidence_submitted", "synthetic evidence attached")
            if flagged.get(sig["id"]) == "NEEDS_APPROVAL":
                ctr.transition("disputed", "margin below review threshold")
                report["disputed"].append(ctr.id)
            else:
                ctr.transition("verified", "evidence accepted")
        else:
            ctr.transition("disputed",
                           f"gate refused: {'; '.join(reasons)}")
            report["disputed"].append(ctr.id)

        report["contracts"].append(ctr)
        report["routed"].append((sig["id"], team_id,
                                 flagged.get(sig["id"], "UNASSIGNED")))

    # 7. HUMAN REVIEW — notify on anything disputed
    if report["disputed"]:
        notify(f"Agentic runner: {len(report['disputed'])} contract(s) need "
               f"human review: {', '.join(report['disputed'])}")

    # chain integrity
    chain_ok = audit.verify_chain()
    return report, chain_ok


def main():
    report, chain_ok = run()
    print("== agentic routing run (synthetic) ==")
    print(f"signals: {len(SIGNALS)} | routable: {len(report['routed'])} "
          f"| noise: {len(report['noise'])}")
    for sig_id, team_id, status in report["routed"]:
        print(f"  {sig_id} -> {team_id} [{status}]")
    print(f"contracts: {len(report['contracts'])}")
    for ctr in report["contracts"]:
        print(f"  {ctr}")
    print(f"disputed (need human): {report['disputed'] or 'none'}")
    print(f"audit chain valid: {chain_ok}")
    assert chain_ok, "audit chain broken"
    print("\nrunner complete: exit 0, no external effects")


if __name__ == "__main__":
    main()

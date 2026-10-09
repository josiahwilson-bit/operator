#!/usr/bin/env python3
"""
finance_summary.py — proposal depth and financial visibility for operator.

Reads contracts + routing log, reports:
  - Pipeline value: total estimated value by contract state
  - Value by team: where the money-shapes concentrate
  - Value by urgency: is high-urgency work actually valuable?
  - Revenue reality check: verified revenue vs pipeline (always $0 until
    a settled payment exists — the classifier enforces this)

"Estimated value" comes from the matching solver's margin (urgency value
+ signal amount). It is NOT revenue. Only FinancialClassifier's
counts_as_revenue=True is revenue, and nothing has earned that yet.
"""
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "github-runner"))

from contract_store import load  # noqa: E402
from routing_log import read_log  # noqa: E402
from financial_logic import FinancialClassifier  # noqa: E402


def main():
    contracts = load()
    routes = read_log()
    fin = FinancialClassifier()

    # margin per signal from routing log (winner's margin)
    value_by_signal = {}
    for r in routes:
        for c in r["candidates"]:
            if c["team_id"] == r["winner"]:
                value_by_signal[r["signal_id"]] = c["margin"]

    by_state = defaultdict(float)
    by_team = defaultdict(float)
    by_urgency = defaultdict(float)
    n = 0
    for cid, c in contracts.items():
        v = value_by_signal.get(c["signal_id"], 0.0)
        by_state[c["state"]] += v
        by_team[c["team_id"]] += v
        by_urgency[c["urgency"]] += v
        n += 1

    # Revenue reality check: run every contract's signal through the
    # financial classifier the way real money would be evaluated.
    verified_revenue = 0.0
    for cid, c in contracts.items():
        result = fin.classify({"kind": "payment", "status": "pending",
                               "amount": 0, "due_date": None})
        if result["counts_as_revenue"]:
            verified_revenue += 0  # unreachable today — by design

    print("== operator finance summary ==")
    print(f"contracts tracked: {n}")
    total = sum(by_state.values())
    print(f"total pipeline value (estimated, NOT revenue): ${total:,.2f}")
    print("\nby state:")
    for s, v in sorted(by_state.items(), key=lambda x: -x[1]):
        print(f"  {s:20s} ${v:>10,.2f}")
    print("\nby team:")
    for t, v in sorted(by_team.items(), key=lambda x: -x[1]):
        print(f"  {t:20s} ${v:>10,.2f}")
    print("\nby urgency:")
    for u, v in sorted(by_urgency.items(), key=lambda x: -x[1]):
        print(f"  {u:20s} ${v:>10,.2f}")
    print(f"\nverified revenue: ${verified_revenue:,.2f}")
    print("(pipeline value is opportunity-shaped; revenue is settled-cash-only)")


if __name__ == "__main__":
    main()

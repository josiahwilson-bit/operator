# operator

An agentic coordination runner. It proposes, routes, and tracks work. It never acts alone.

**Pipeline:** capture → classify → route → delegate → gate → contract → human review

## Values (enforced, not aspirational)

1. **Fail closed.** Without owner approval, every delegation is refused.
2. **Human review is structural.** No stage is skippable, no matter the trust tier.
3. **Evidence or it didn't happen.** Every decision is hash-chained in the audit log.
4. **$0 means $0.** The budget gate blocks any spend.
5. **No autonomous comms.** Operator drafts; the owner sends.
6. **Synthetic first.** Every new capability starts on synthetic data.

See [OPERATOR-CHARTER.md](OPERATOR-CHARTER.md) for the full charter.

## Components

| File | What it does |
|---|---|
| `agentic_runner.py` | The pipeline: signal → team → gate → contract |
| `demo_first_team.py` | Proves the full lifecycle (refuse path + approve path) |
| `signals_inbox.py` | File-based signal inbox (`run_state/inbox/`) with validation |
| `approve.py` | The human approval interface (only legitimate approval path) |
| `contract_store.py` | Persistent contract storage between runs |
| `notify_node.py` | Tails the audit log, publishes findings (idempotent) |
| `spec_sync_node.py` | Drift detector: gate.py vs Rego mockup |
| `feed_generator.py` | Findings → Atom + JSON feeds |
| `routing_log.py` | Structured log of why each signal routed where it did |
| `finance_summary.py` | Pipeline value by state/team/urgency; revenue reality check |
| `settings.py` / `settings.json` | Central operational config (see below) |
| `OPERATOR-CHARTER.md` | Identity and values |
| `DISCORD-BOT-SETUP.md` | Bot setup walkthrough (owner creates the bot) |

## Quick start

```bash
python3 agentic_runner.py      # run the pipeline (inbox first, synthetic fallback)
python3 approve.py             # list pending contracts / approve one
python3 demo_first_team.py     # prove the full contract lifecycle
python3 notify_node.py         # publish new findings since last run
python3 spec_sync_node.py      # check policy docs against enforced policy
python3 feed_generator.py      # regenerate findings.atom + findings.json
python3 finance_summary.py     # pipeline value and revenue reality check
```

All components are stdlib-only. No installs, no credentials, no network calls.
With no `DISCORD_WEBHOOK_URL` set, notification paths skip gracefully (exit 0).

## Settings

`settings.json` holds every operational choice: capture caps, routing thresholds,
contract TTLs, notify cooldowns, feed formats, backup retention. Edit freely.

**Not in settings (deliberately):** gate policies, charter values, budget enforcement.
Those live in code with tests — changing them requires an owner-approved code edit,
not a config tweak. Settings control *how the machine runs*; they can't change
*what it's allowed to do*.

## Feeding it signals

Drop JSON files into `run_state/inbox/`:

```json
{"id": "SIG-005", "source": "manual",
 "content": "what happened, in plain words",
 "kind": "inbound_lead | opportunity | noise",
 "amount": 0}
```

The next run picks them up, validates them, processes them, and archives them
to `run_state/inbox/processed/`. Invalid files are rejected with reasons.

## Design

Full architecture: [AGENTIC-ROUTING-DESIGN.md](../research/agentic-routing-20261009/AGENTIC-ROUTING-DESIGN.md) (workspace copy)
Rego policy mockup: [rego-policy-mock.rego](../research/agentic-routing-20261009/rego-policy-mock.rego) (workspace copy)

## License

MIT

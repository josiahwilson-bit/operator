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
| `notify_node.py` | Tails the audit log, publishes findings (idempotent) |
| `feed_generator.py` | Findings → Atom + JSON feeds |
| `OPERATOR-CHARTER.md` | Identity and values |
| `DISCORD-BOT-SETUP.md` | Bot setup walkthrough (owner creates the bot) |

## Quick start

```bash
python3 agentic_runner.py      # run the pipeline (synthetic, $0, no external effects)
python3 demo_first_team.py     # prove the full contract lifecycle
python3 notify_node.py         # publish new findings since last run
python3 feed_generator.py      # regenerate findings.atom + findings.json
```

All components are stdlib-only. No installs, no credentials, no network calls.
With no `DISCORD_WEBHOOK_URL` set, notification paths skip gracefully (exit 0).

## Design

Full architecture: [AGENTIC-ROUTING-DESIGN.md](../research/agentic-routing-20261009/AGENTIC-ROUTING-DESIGN.md) (workspace copy)
Rego policy mockup: [rego-policy-mock.rego](../research/agentic-routing-20261009/rego-policy-mock.rego) (workspace copy)

## License

MIT

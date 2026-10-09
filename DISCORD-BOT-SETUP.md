# operator Discord Bot — Setup Walkthrough

**You** do these steps (I can't create the bot — it's your Discord account).
**Time:** ~10 minutes. **Cost:** $0.

## Part 1 — Create the bot (your hands)

1. Go to https://discord.com/developers/applications
2. **New Application** → name it `operator` → Create
3. Left sidebar → **Bot** → **Reset Token** → **copy the token**
   - This token is a credential. Paste it into Secure Vault — never into chat, email, or a doc.
4. On the Bot page, turn OFF everything under "Privileged Gateway Intents" (operator doesn't need them)
5. Left sidebar → **OAuth2 → URL Generator**:
   - Scopes: check `bot`
   - Bot Permissions: check `Send Messages` and `Read Message History` only — nothing else
   - Copy the generated URL at the bottom
6. Open that URL → select your server → Authorize
7. `operator` now appears in your server (offline until code connects it)

## Part 2 — Token wiring (tell me when Part 1 is done)

Once the token is in Secure Vault:
- I wire it into the runner's environment (never into code or logs)
- `discord_notify.py` already reads from env — it goes live with zero code changes
- The notify node starts publishing findings to your channel

## What operator can and can't do on Discord

| Can | Can't |
|---|---|
| Post findings to a channel you choose | DM anyone |
| Post gate-refusal alerts | Join other servers |
| Identify itself as a bot in every message | Delete or edit messages |
| Stay silent when there's nothing new | Send without a finding to report |

## Safety notes

- The bot has only Send Messages + Read History. It cannot manage the server, ban, or read DMs.
- If the token ever leaks: Discord Developer Portal → Bot → Reset Token → update Secure Vault. 2 minutes.
- To remove operator entirely: Server Settings → Integrations → Bots → Remove. No trace left.

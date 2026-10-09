#!/usr/bin/env python3
"""
Feed generator for operator findings.

Reads run_state/findings.log, emits:
  - findings.atom  (Atom 1.0 feed — subscribable in any feed reader)
  - findings.json  (JSON Feed 1.1 — for dashboards/widgets)

Pure stdlib. No server. Regenerate on demand or via cron.
Idempotent: same findings.log -> same feed output.
"""
import json
import os
import re
from datetime import datetime, timezone
from xml.sax.saxutils import escape

HERE = os.path.dirname(os.path.abspath(__file__))
RUN = os.path.join(HERE, "run_state")
FINDINGS = os.path.join(RUN, "findings.log")

FEED_ID = "urn:operator:findings"
FEED_TITLE = "operator findings"


def parse_findings():
    """Parse '[ts] CONTRACT decision=X team=tier:Y :: reason' lines."""
    entries = []
    if not os.path.exists(FINDINGS):
        return entries
    with open(FINDINGS) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            m = re.match(r"\[(.*?)\]\s+(\S+)\s+decision=(\S+)\s+"
                         r"team=(\S+)\s+::\s*(.*)", line)
            if m:
                ts, contract, decision, team, reason = m.groups()
                entries.append({"ts": ts, "contract": contract,
                                "decision": decision, "team": team,
                                "reason": reason or "(no reason recorded)"})
            else:
                entries.append({"ts": "", "contract": "unknown",
                                "decision": "unknown", "team": "unknown",
                                "reason": line})
    return entries


def to_atom(entries):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    items = []
    for e in entries:
        ts = e["ts"] or now
        # normalize ts to RFC3339 if it parses, else use now
        try:
            datetime.fromisoformat(ts)
            rfc = ts if ts.endswith("Z") else ts + "Z"
        except ValueError:
            rfc = now
        title = f"{e['contract']} — {e['decision']}"
        items.append(
            f"  <entry>\n"
            f"    <title>{escape(title)}</title>\n"
            f"    <id>{FEED_ID}:{escape(e['contract'])}:{escape(rfc)}</id>\n"
            f"    <updated>{escape(rfc)}</updated>\n"
            f"    <summary>{escape(e['reason'])} "
            f"(team: {escape(e['team'])})</summary>\n"
            f"  </entry>")
    return (
        f'<?xml version="1.0" encoding="utf-8"?>\n'
        f'<feed xmlns="http://www.w3.org/2005/Atom">\n'
        f"  <title>{escape(FEED_TITLE)}</title>\n"
        f"  <id>{FEED_ID}</id>\n"
        f"  <updated>{now}</updated>\n"
        + "\n".join(items) +
        f"\n</feed>\n")


def to_json_feed(entries):
    items = [{"id": f"{FEED_ID}:{e['contract']}:{e['ts']}",
              "title": f"{e['contract']} — {e['decision']}",
              "content_text": f"{e['reason']} (team: {e['team']})",
              "date_published": e["ts"] or None}
             for e in entries]
    return json.dumps({"version": "https://jsonfeed.org/version/1.1",
                       "title": FEED_TITLE,
                       "home_page_url": "",
                       "feed_url": "",
                       "items": items}, indent=2)


def main():
    entries = parse_findings()
    atom_path = os.path.join(RUN, "findings.atom")
    json_path = os.path.join(RUN, "findings.json")
    with open(atom_path, "w") as f:
        f.write(to_atom(entries))
    with open(json_path, "w") as f:
        f.write(to_json_feed(entries))
    print(f"feed: {len(entries)} entries -> "
          f"{os.path.basename(atom_path)}, {os.path.basename(json_path)}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
settings.py — single configuration loader for operator.

Reads settings.json. All values have code defaults so a missing or
corrupt settings file never breaks a run — the runner falls back to
defaults and reports which file it used.

Security boundary: this file carries OPERATIONAL settings only
(TTLs, thresholds, cooldowns, formats). Gate policies, charter values,
and budget enforcement are NOT configurable here — they live in
gate.py and the charter, changeable only by owner-approved code edits.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "settings.json")

DEFAULTS = {
    "capture": {
        "synthetic_fallback": True,
        "auto_archive": True,
        "max_signals_per_run": 50,
    },
    "routing": {
        "review_threshold_margin": 500.0,
        "source_skills": {
            "mastodon": ["web"],
            "reddit": ["web"],
            "webhook": ["data"],
            "email": ["data"],
            "manual": ["web", "data"],
        },
    },
    "contracts": {
        "ttl_hours": {"critical": 4, "high": 24, "normal": 72, "low": 168},
    },
    "notify": {
        "cooldown_minutes": 15,
        "digest_threshold": 5,
        "max_per_hour": 20,
    },
    "feeds": {
        "formats": ["atom", "json"],
    },
    "maintenance": {
        "backup_retention": 10,
        "log_verbosity": "info",
    },
}


def _deep_merge(base, override):
    out = dict(base)
    for k, v in override.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load():
    """Return (settings, source) where source is 'settings.json',
    'defaults (settings.json missing)', or 'defaults (settings.json invalid)'."""
    if not os.path.exists(PATH):
        return dict(DEFAULTS), "defaults (settings.json missing)"
    try:
        with open(PATH) as f:
            user = json.load(f)
    except (json.JSONDecodeError, OSError):
        return dict(DEFAULTS), "defaults (settings.json invalid)"
    user.pop("_comment", None)
    return _deep_merge(DEFAULTS, user), "settings.json"


def get(*keys):
    """get('notify', 'cooldown_minutes') -> value."""
    s, _ = load()
    for k in keys:
        s = s[k]
    return s

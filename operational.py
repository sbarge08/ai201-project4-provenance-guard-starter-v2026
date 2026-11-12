"""Append-only request lifecycle events, separate from classification audits."""

import json
import threading

import config

_lock = threading.Lock()


def log_request_event(entry: dict) -> dict:
    """Append one request event as a JSONL record."""
    config.OPERATIONAL_LOG.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(entry, ensure_ascii=False)
    with _lock:
        with config.OPERATIONAL_LOG.open("a", encoding="utf-8") as log_file:
            log_file.write(line + "\n")
    return entry

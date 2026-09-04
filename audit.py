import json
from datetime import datetime
from pathlib import Path

AUDIT_FILE = Path(__file__).parent / "audit_log.json"


def log_event(event, details=None):
    if AUDIT_FILE.exists():
        try:
            with open(AUDIT_FILE, "r", encoding="utf-8") as file:
                logs = json.load(file)
        except (json.JSONDecodeError, OSError):
            logs = []
    else:
        logs = []

    logs.append({
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "event": event,
        "details": details or {}
    })

    with open(AUDIT_FILE, "w", encoding="utf-8") as file:
        json.dump(logs, file, indent=2, ensure_ascii=False)


def get_audit_log():
    if not AUDIT_FILE.exists():
        return []

    try:
        with open(AUDIT_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except (json.JSONDecodeError, OSError):
        return []

"""Minimal settings persistence."""
from pathlib import Path
import json

SETTINGS_PATH = Path.home() / ".config" / "pyagents" / "settings.json"


def load() -> dict:
    """Load all settings."""
    if SETTINGS_PATH.exists():
        return json.loads(SETTINGS_PATH.read_text())
    return {}


def save(data: dict) -> None:
    """Save all settings."""
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(data, indent=2))


def get(key: str, default=None):
    """Get a single setting."""
    return load().get(key, default)


def set(key: str, value) -> None:
    """Set a single setting."""
    data = load()
    data[key] = value
    save(data)

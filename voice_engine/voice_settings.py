"""
Voice settings loader - auto-loads tuned settings from voice_settings.json if available.
"""

import json
from pathlib import Path
from typing import Optional, Dict, Any


def get_settings_path() -> Path:
    """Get the path to the voice settings JSON file."""
    return Path(__file__).parent / "voice_settings.json"


def load_settings() -> Optional[Dict[str, Any]]:
    """Load saved voice settings from JSON."""
    settings_path = get_settings_path()
    if settings_path.exists():
        try:
            with open(settings_path) as f:
                return json.load(f)
        except Exception:
            return None
    return None


def get_setting(key: str, default: Any) -> Any:
    """Get a single setting value, falling back to default if not found."""
    settings = load_settings()
    if settings:
        return settings.get(key, default)
    return default

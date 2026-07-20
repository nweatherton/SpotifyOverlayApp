# settings.py
#
# Loads/saves the overlay's appearance settings as a small JSON file so your
# preferences (colors, size, opacity, etc.) persist between runs.

import json
import os

from app_config import config_dir

SETTINGS_FILE = os.path.join(config_dir(), "overlay_settings.json")

DEFAULTS = {
    "width": 760,
    "height": 170,               # actual overlay height (no forced minimum anymore -
                                  # you can shrink this as far as you like; the content
                                  # adapts, see overlay.py's responsive layout logic)
    "font_size": 20,
    "text_color": "#FFFFFF",       # current lyric line
    "next_text_color": "#B0B0B0",  # upcoming lyric line (preview)
    "button_color": "#FFFFFF",     # prev/next button icon color
    "bg_color": "#000000",
    "bg_opacity": 140,             # 0 (invisible) - 255 (solid)
    "sync_offset_ms": 0,
    "click_through": False,
}


def load_settings():
    """Returns saved settings merged over the defaults (so new options
    added later always have a sane value even with an old settings file)."""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                saved = json.load(f)
            merged = DEFAULTS.copy()
            merged.update(saved)
            return merged
        except (json.JSONDecodeError, OSError) as e:
            print(f"[settings] couldn't read {SETTINGS_FILE}, using defaults: {e}")
    return DEFAULTS.copy()


def save_settings(settings):
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f, indent=2)
    except OSError as e:
        print(f"[settings] failed to save: {e}")
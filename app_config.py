# app_config.py
#
# Where this app keeps anything that has to persist between runs and be
# writable even when the app itself is a single .exe living somewhere
# read-only (like Program Files) or launched from a random working
# directory (like a desktop shortcut): a per-user folder, same idea as
# every other Windows app uses %APPDATA% for.
#
# This is also where each person's own Spotify Client ID/Secret are saved
# after they go through the one-time setup wizard (setup_wizard.py) - so
# secrets never need to be baked into the exe or the source code shared
# with anyone else.

import json
import os

REDIRECT_URI = "http://127.0.0.1:8888/callback"

_CREDENTIALS_FILENAME = "spotify_credentials.json"
_TOKEN_CACHE_FILENAME = ".spotify_cache"


def config_dir():
    base = os.getenv("APPDATA") or os.path.expanduser("~")
    path = os.path.join(base, "SpotifyLyricsOverlay")
    os.makedirs(path, exist_ok=True)
    return path


def credentials_path():
    return os.path.join(config_dir(), _CREDENTIALS_FILENAME)


def token_cache_path():
    return os.path.join(config_dir(), _TOKEN_CACHE_FILENAME)


def has_credentials():
    return os.path.exists(credentials_path())


def load_credentials():
    """Returns (client_id, client_secret), or (None, None) if not set up yet."""
    if not has_credentials():
        return None, None
    try:
        with open(credentials_path(), "r") as f:
            data = json.load(f)
        client_id = data.get("client_id")
        client_secret = data.get("client_secret")
        if not client_id or not client_secret:
            return None, None
        return client_id, client_secret
    except (json.JSONDecodeError, OSError):
        return None, None


def save_credentials(client_id, client_secret):
    with open(credentials_path(), "w") as f:
        json.dump(
            {"client_id": client_id.strip(), "client_secret": client_secret.strip()},
            f,
            indent=2,
        )


def clear_credentials():
    """Removes the saved credentials AND the cached Spotify login token, so
    the next SpotifyClient() forces a full fresh setup + browser login."""
    for path in (credentials_path(), token_cache_path()):
        try:
            os.remove(path)
        except OSError:
            pass

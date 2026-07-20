# spotify_client.py
#
# Thin wrapper around spotipy that logs the user in (once, via browser),
# exposes the currently playing track + playback position, and lets you
# skip to the next/previous track.

import spotipy
from spotipy.oauth2 import SpotifyOAuth

from app_config import load_credentials, REDIRECT_URI, token_cache_path

# NOTE: user-modify-playback-state was added so next_track()/previous_track()
# below are allowed. Since this is a new scope, delete your .spotify_cache
# file once after pulling this change so you get re-prompted to approve it
# (otherwise you'll get a 403 "insufficient scope" the first time you skip).
SCOPE = "user-read-currently-playing user-read-playback-state user-modify-playback-state"


class SpotifyClient:
    def __init__(self):
        client_id, client_secret = load_credentials()
        if not client_id or not client_secret:
            # Shouldn't normally happen - main.py runs the setup wizard
            # before this is ever constructed - but fail with a clear
            # message instead of a confusing spotipy error if it does.
            raise RuntimeError(
                "No Spotify credentials found. Run the app again to go "
                "through setup, or use the tray icon's 'Reconfigure "
                "Spotify...' option."
            )
        self.sp = spotipy.Spotify(
            auth_manager=SpotifyOAuth(
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri=REDIRECT_URI,
                scope=SCOPE,
                cache_path=token_cache_path(),
                open_browser=True,
            )
        )

    def get_current_track(self):
        """
        Returns a dict describing what's currently playing, or None if
        nothing is playing / the user isn't active on Spotify right now.
        """
        try:
            playback = self.sp.current_playback()
        except Exception as e:
            print(f"[spotify] API error: {e}")
            return None

        if not playback or not playback.get("item"):
            return None

        item = playback["item"]
        images = (item.get("album", {}) or {}).get("images") or []
        album_art_url = images[-1]["url"] if images else None  # smallest available image
        return {
            "id": item["id"],
            "title": item["name"],
            "artist": ", ".join(a["name"] for a in item["artists"]),
            "album": item["album"]["name"],
            "duration_ms": item["duration_ms"],
            "progress_ms": playback.get("progress_ms") or 0,
            "is_playing": playback.get("is_playing", False),
            "album_art_url": album_art_url,  # NOTE: overlay.py reads this exact key name - keep them in sync
        }

    def next_track(self):
        """
        Skips to the next track on whatever device is currently active.
        Returns True on success, False if the call failed (e.g. no active
        device, a free/non-Premium account, or an API error).
        """
        try:
            self.sp.next_track()
            return True
        except Exception as e:
            print(f"[spotify] Error skipping to next track: {e}")
            return False

    def previous_track(self):
        """
        Goes back to the previous track on whatever device is currently
        active. Returns True on success, False if the call failed (e.g. no
        active device, a free/non-Premium account, or an API error).
        """
        try:
            self.sp.previous_track()
            return True
        except Exception as e:
            print(f"[spotify] Error skipping to previous track: {e}")
            return False
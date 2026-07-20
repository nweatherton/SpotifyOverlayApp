# lyrics.py
#
# Fetches lyrics from lrclib.net (free, no API key/auth needed) and parses
# synced (.lrc) lyrics into a list of (timestamp_seconds, line_text) tuples.

import re
import requests

LRCLIB_BASE = "https://lrclib.net/api"
HEADERS = {"User-Agent": "spotify-lyrics-overlay/1.0 (personal use)"}

_TIMESTAMP_RE = re.compile(r"\[(\d{2}):(\d{2})(?:[.:](\d{2,3}))?\]")


def fetch_lyrics(title, artist, album, duration_ms):
    """
    Returns one of:
      {"type": "synced", "lines": [(seconds, text), ...]}
      {"type": "plain", "text": "..."}
      None  (no lyrics found anywhere)
    """
    duration_sec = round(duration_ms / 1000)

    # 1. Try an exact match first (matches on title/artist/album/duration).
    try:
        resp = requests.get(
            f"{LRCLIB_BASE}/get",
            params={
                "track_name": title,
                "artist_name": artist,
                "album_name": album,
                "duration": duration_sec,
            },
            headers=HEADERS,
            timeout=5,
        )
        if resp.status_code == 200:
            parsed = _parse_response(resp.json())
            if parsed:
                return parsed
    except requests.RequestException as e:
        print(f"[lyrics] exact lookup failed: {e}")

    # 2. Fall back to fuzzy search (e.g. album name mismatch, singles, etc.)
    try:
        resp = requests.get(
            f"{LRCLIB_BASE}/search",
            params={"track_name": title, "artist_name": artist},
            headers=HEADERS,
            timeout=5,
        )
        if resp.status_code == 200:
            results = resp.json()
            if results:
                return _parse_response(results[0])
    except requests.RequestException as e:
        print(f"[lyrics] search fallback failed: {e}")

    return None


def _parse_response(data):
    synced = data.get("syncedLyrics")
    plain = data.get("plainLyrics")
    if synced:
        lines = parse_lrc(synced)
        if lines:
            return {"type": "synced", "lines": lines}
    if plain:
        return {"type": "plain", "text": plain}
    return None


def parse_lrc(lrc_text):
    """Parses LRC-format text into a time-sorted list of (seconds, line)."""
    lines = []
    for raw_line in lrc_text.splitlines():
        matches = list(_TIMESTAMP_RE.finditer(raw_line))
        if not matches:
            continue
        text = _TIMESTAMP_RE.sub("", raw_line).strip()
        for m in matches:
            minutes, seconds, frac = m.group(1), m.group(2), m.group(3)
            frac_val = float(f"0.{frac}") if frac else 0.0
            timestamp = int(minutes) * 60 + int(seconds) + frac_val
            lines.append((timestamp, text))
    lines.sort(key=lambda pair: pair[0])
    return lines

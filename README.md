# Spotify Lyrics Overlay
REQUIRES SPOTIFY PREMIUM TO USE
A small always-on-top bar that shows synced lyrics for whatever's playing
on your Spotify account, so you can leave it floating over a game, a
browser, whatever.

Built with:
- The **Spotify Web API** for what's playing and how far into it you are
- [**lrclib.net**](https://lrclib.net) (free, no key needed) for synced lyrics
- **PyQt5** for the overlay window itself

## Running it from source

```
pip install -r requirements.txt
python main.py
```

First run, a setup window walks you through creating a free Spotify "app"
— Spotify requires this for anything that reads what's playing, there's
no way around it. It's a couple minutes: log into the Spotify dashboard,
click Create app, paste in a redirect URI (the wizard gives you the exact
one to use), and copy two codes back into the window. You only do this
once — after that it just remembers you.

Everything it saves (your Spotify keys, your login session, your overlay
settings) lives in `%APPDATA%\SpotifyLyricsOverlay\` on your own machine.
None of it goes in this repo or anywhere but Spotify.

Want to redo setup (wrong app, typo, switching accounts)? Right now the
only way is deleting that `%APPDATA%\SpotifyLyricsOverlay\` folder and
relaunching — a menu option for this is on the list.

## Just want the .exe?

See [`dist/SpotifyLyricsOverlay.exe`](dist/SpotifyLyricsOverlay.exe) — for
a ready to download executable file from the latest version.

See [`BUILD_AND_SHARE.md`](BUILD_AND_SHARE.md) — build it once on a
machine with Python, then it's a single file anyone can double-click,
no Python required on their end.

## Using it

- **Drag** anywhere on the bar to move it.
- **Prev / next buttons** on either side skip tracks.
- **Right-click the tray icon** (bottom-right, near the clock) for
  Settings, About/Info, and Quit.

### Settings

Tray icon → Settings gets you a small panel, applied live:

- Width, height, font size
- Text color, next-line color, background color, button color
- Background opacity
- Sync offset, in case lyrics ever feel a beat early or late
- Center overlay / reset to defaults

Shrink the window down (~300×60) and it drops the lyrics, showing just
track/artist. Shrink it further (~180×60) and it drops to just the album
art. Nothing to configure for this — it's just based on how much room
you give it.

## Things worth knowing

**Exclusive fullscreen games won't show it.** Windows only lets other
windows draw over borderless/windowed apps — true exclusive fullscreen
takes the whole screen and nothing renders above it. Switch the game to
Borderless Windowed and you're fine.

**Anti-cheat.** This is just an ordinary window, same as Discord or
RTSS — generally not something anti-cheat flags. Still worth checking a
game's stance before relying on it in ranked/competitive modes.

**Lyrics aren't guaranteed.** lrclib.net is community-sourced — great
coverage for popular music, spottier for niche tracks, remixes, or local
files. When nothing's found you'll see the track/artist instead, or
unsynced lyrics if that's all that's available.

**Polling.** It checks Spotify every 3 seconds and estimates your
position in between off its own clock, so it stays smooth without
hammering the API.

## Tweaking the code

- Default position: `self.move(...)` in `overlay.py`'s `_init_ui`
- Font/colors: same file, the `QFont(...)` / stylesheet calls
- Click-through (clicks pass through to whatever's underneath, so you
  can't accidentally drag it mid-game): there's a `click_through` field
  in `overlay_settings.json` but no UI toggle yet — set it to `true` by
  hand in that file if you want it now.

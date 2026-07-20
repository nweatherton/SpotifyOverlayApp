# Spotify Lyrics Overlay

A small always-on-top window that shows synced lyrics for whatever is
currently playing on your Spotify account, so you can leave it floating
over a game or anything else you're doing.

It uses:
- The official **Spotify Web API** to see what track is playing and how
  far into it you are.
- The free, keyless **lrclib.net** API to fetch synced lyrics.
- **PyQt5** for the floating window.

---

## 1. Create a Spotify Developer app

You need this so the app is allowed to ask Spotify "what's playing right now."

1. Go to https://developer.spotify.com/dashboard and log in with your
   normal Spotify account.
2. Click **Create app**.
3. Fill in any App name / description (e.g. "Lyrics Overlay").
4. Under **Redirect URIs**, add exactly:
   ```
   http://127.0.0.1:8888/callback
   ```
   Use `127.0.0.1`, not `localhost` — Spotify only allows the literal
   loopback IP for local testing now.
5. Check the box for **Web API** when asked which API you're using, agree
   to the terms, and click **Save**.
6. On the app's page, click **Settings**. You'll see your **Client ID**,
   and a button to reveal your **Client Secret**.

## 2. Add your credentials

Open `config.py` and paste in your values:

```python
SPOTIFY_CLIENT_ID = "paste your client id here"
SPOTIFY_CLIENT_SECRET = "paste your client secret here"
SPOTIFY_REDIRECT_URI = "http://127.0.0.1:8888/callback"
```

## 3. Install dependencies

Open a terminal in this folder and run:

```
pip install -r requirements.txt
```

## 4. Run it

```
python main.py
```

The first time you run it, a browser window will open asking you to log
in to Spotify and approve access. After you approve, it caches the login
token in a local `.spotify_cache` file, so you won't have to log in again.

You should then see a small dark, semi-transparent bar appear near the
bottom of your screen showing the current lyric line.

### Controls
- **Drag** the bar by clicking and holding anywhere on it.
- **Esc** while it's focused quits the app.
- **Right-click the tray icon** (near your clock, in the hidden icons area)
  for **Settings...** and **Quit**.

### Settings panel

Right-click the tray icon → **Settings...** to open a small always-on-top
panel where you can change, live:

- **Overlay width** and **font size**
- **Text color** (current line), **next-line color**, and **background
  color** (click the color swatches)
- **Background opacity**
- **Lyric sync offset** — nudge timing earlier/later in milliseconds if it
  ever feels a beat off
- **Click-through** — lets clicks pass through the overlay to whatever's
  underneath (e.g. so you don't accidentally click it mid-game). You can
  still reach Settings/Quit from the tray icon while this is on.
- **Center overlay** button, in case you've dragged it somewhere awkward
- **Reset to defaults**

Everything you change is saved to `overlay_settings.json` in this folder,
so it's remembered the next time you run the app.

The window's **height adjusts automatically** to fit however many lines
the current lyric wraps to — no wasted empty space, and it grows/shrinks
from the same anchored spot on screen instead of jumping around.

---

## Important things to know

**Games in true exclusive fullscreen won't show the overlay.** Windows
only lets other windows draw on top of borderless/windowed apps — a game
running in real exclusive fullscreen takes over the whole screen and
nothing (including this) can render above it. If the overlay doesn't
show up over your game, switch that game's display mode to **Borderless
Windowed** (sometimes called "Windowed Fullscreen") in its video
settings, and it'll work fine.

**Anti-cheat in competitive multiplayer games.** This is just an
ordinary on-screen window like any other app (Discord, RTSS, etc. work
the same way), so it's generally not something anti-cheat systems flag.
That said, if you play something with strict anti-cheat, it's worth
double-checking that game's stance on third-party overlays before
relying on this while playing ranked/competitive modes.

**Lyrics won't always be found.** lrclib.net is a community-maintained,
crowdsourced database — very good coverage for popular music, but some
niche tracks, remixes, or local files won't have synced lyrics. When
that happens the overlay will say "No lyrics found," or show unsynced
lyrics if only those are available.

**Polling rate.** The app checks Spotify's real position every 3 seconds
and smoothly estimates your position in between using its own clock, so
the display stays responsive without hammering the API.

---

## Customizing

A few easy tweaks, all in `overlay.py`:
- **Position**: change the numbers in `self.move(...)` inside `_init_ui`.
- **Font size / color**: edit the `QFont(...)` and `setStyleSheet(...)`
  calls on `label_current` / `label_next`.
- **Opacity of the background bar**: change the `140` in
  `QColor(0, 0, 0, 140)` inside `paintEvent` (0 = fully transparent,
  255 = solid).
- **Click-through mode** (so clicks pass through to the game underneath
  and you can't accidentally drag it): add
  `self.setAttribute(Qt.WA_TransparentForMouseEvents)` in `_init_ui`.
  You'd then need to reposition it by editing the move() coordinates
  directly, since you can no longer drag it with the mouse.

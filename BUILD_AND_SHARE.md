# Turning this into an .exe anyone can run

Two different people, two different jobs:

- **You** (or whoever has this code) build the exe once. That machine
  needs Python installed.
- **Anyone you share the exe with** just double-clicks it. They need
  nothing installed - no Python, no code, nothing.

## 1. Build it (one time)

1. Make sure Python is installed on your machine (python.org - during
   install, check "Add python.exe to PATH").
2. Double-click **`build_exe.bat`** in this folder.
3. Wait a minute or two while it installs packages and builds.
4. Your exe is now at `dist\SpotifyLyricsOverlay.exe`.

You can safely delete the old `config.py` file if you still have one lying
around from before - it's not used anymore (see below).

## 2. Share it

Copy just `dist\SpotifyLyricsOverlay.exe` - that single file - to anyone:
USB drive, Discord, email, whatever. That's the entire app.

## 3. What happens when someone runs it

The first time anyone (including you) runs the exe:

1. A window pops up explaining that Spotify requires a free "app"
   registration to allow the program to read what's playing.
2. It links straight to the Spotify Developer Dashboard and walks through
   the ~2-minute steps in plain English (create an app, paste in one
   fixed Redirect URI, copy two codes back into the wizard).
3. Once saved, the overlay starts normally and remembers those codes for
   next time - the wizard never shows again unless they use "Reconfigure
   Spotify..." from the tray icon menu (e.g. to fix a typo or switch
   accounts).

Everything (their Spotify keys, the overlay's settings, the Spotify login
token) is stored in `%APPDATA%\SpotifyLyricsOverlay\` on their own
computer - never bundled into the exe, never sent anywhere but Spotify.

## Why each person needs their own Spotify "app"

Spotify requires every program that talks to their API to be registered,
and it has to be done through a real Spotify account in a browser - there's
no way to script around that part, and it can't be done once on your end
for everyone else, since Spotify caps how many people can use a single
unapproved "app" (25 in Spotify's free/development mode). Registering one
takes about 2 minutes and is exactly what the wizard walks them through -
it's free, and it isn't a subscription or anything Spotify charges for.

## If the build fails

- **`ModuleNotFoundError: No module named 'PyQt5'` when you run the exe**:
  this means `pip` and `pyinstaller` used two different Python installs
  when you built it - very common if you have more than one Python on your
  machine (e.g. the Microsoft Store version alongside python.org's). The
  script now runs everything through `python -m pip` / `python -m
  PyInstaller` and checks `python -c "import PyQt5"` *before* building, so
  a mismatch shows up immediately as a clear error instead of surfacing
  later inside the exe. If that preflight check itself fails, run
  `python -m pip install PyQt5` and read what it says - you may have a
  Python install that isn't the one on your PATH.
- **"pyinstaller not recognized"**: close and reopen the terminal/Command
  Prompt after installing Python, or restart your computer once - PATH
  changes sometimes need that.
- **Windows Defender/SmartScreen flags the exe**: normal for any
  unsigned/homemade exe. Click "More info" -> "Run anyway". Signing an
  exe costs money and isn't necessary for sharing with friends.
- **Exe opens then instantly closes**: run it from a Command Prompt
  instead of double-clicking (`dist\SpotifyLyricsOverlay.exe`) so you can
  actually read the error, then share that error if you want help fixing
  it.

@echo off
setlocal

echo Checking Python...
python --version
if errorlevel 1 (
    echo.
    echo Python isn't on PATH. Install it from python.org ^(check "Add
    echo python.exe to PATH" during setup^), then run this again.
    pause
    exit /b 1
)

echo.
echo Cleaning up any previous build...
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul
del /q SpotifyLyricsOverlay.spec 2>nul

echo.
echo Installing required packages with "python -m pip" so they go to the
echo SAME Python that will build the exe - a mismatch here (e.g. a "pip"
echo command pointing at a different Python than "python" does) is the
echo #1 cause of "ModuleNotFoundError: No module named 'PyQt5'" showing
echo up later, inside the built exe.
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pyinstaller

echo.
echo Double-checking PyQt5 actually imports in this Python...
python -c "import PyQt5; print('PyQt5 OK:', PyQt5.__file__)"
if errorlevel 1 (
    echo.
    echo PyQt5 isn't importable here - fix the error above first. Building
    echo the exe would just fail the same way, later and more confusingly.
    pause
    exit /b 1
)

echo.
echo Building SpotifyLyricsOverlay.exe ...
python -m PyInstaller --noconfirm --onefile --windowed --name "SpotifyLyricsOverlay" --collect-all PyQt5 --paths=. main.py

echo.
if exist dist\SpotifyLyricsOverlay.exe (
    echo Done! Your exe is at: dist\SpotifyLyricsOverlay.exe
    echo Share just that one file - nobody else needs Python installed.
) else (
    echo Something went wrong - scroll up for the error from PyInstaller.
)
pause
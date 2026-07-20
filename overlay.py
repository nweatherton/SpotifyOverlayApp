import time
import requests
from PyQt5.QtWidgets import (
    QWidget, QApplication, QLabel, QVBoxLayout, QHBoxLayout,
    QLayout, QSystemTrayIcon, QMenu, QAction, QStyle, QPushButton,
    QDialog, QMessageBox
)
from PyQt5.QtCore import Qt, QTimer, QPoint, QThreadPool, QRunnable, QObject, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QPainter, QImage, QPixmap, QIcon, QPolygon
from spotify_client import SpotifyClient
from lyrics import fetch_lyrics
from settings import load_settings, save_settings
from settings_dialog import SettingsDialog
from setup_wizard import SetupWizard
from app_config import clear_credentials

POLL_INTERVAL_MS = 3000  # safe to poll more often now that it's off the UI thread
RENDER_INTERVAL_MS = 100

# Gaps involved in the vertical "squeeze" as the overlay is asked to be
# shorter than its comfortable content height. They're squeezed in this
# order: bottom margin -> gap between the two lyric lines -> top margin.
# Once all three are at their minimum and it's still too short, the
# preview (next) lyric line is hidden entirely rather than clipped. The
# current (top) lyric line is never clipped - if even that minimum needs
# more room than the target, the overlay grows to fit it.
MARGIN_TOP_MAX, MARGIN_TOP_MIN = 12, 2
MARGIN_BOTTOM_MAX, MARGIN_BOTTOM_MIN = 4, 0
LYRIC_GAP_MAX, LYRIC_GAP_MIN = 10, 0
TOP_GAP = 8 
TOP_GAP_MAX, TOP_GAP_MIN = 8, 2
SIDE_MARGIN = 12
ART_INFO_COMPACT_BUFFER = 24  # extra breathing room before flipping to compact mode
ART_SIZE = 32
DEFAULT_WIDTH = 600
DEFAULT_HEIGHT = 170

class WorkerSignals(QObject):
    track_ready = pyqtSignal(object)
    lyrics_ready = pyqtSignal(str, object)
    art_ready = pyqtSignal(str, object)

class Worker(QRunnable):
    """Runs fn(*args, **kwargs) on a background thread from Qt's thread pool,
    so slow network calls (Spotify, lyrics, album art) never freeze the UI."""
    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            self.fn(*self.args, **self.kwargs)
        except Exception as e:
            print(f"[worker] unhandled error: {e}")

class LyricsOverlay(QWidget):
    
    def __init__(self):
        super().__init__()
        self.settings = load_settings()
        self.spotify = SpotifyClient()
        self.current_track_id = None
        self.lyrics_data = None
        self.last_track = None
        self.drag_pos = None
        self._is_compact_mode = None
        self.settings_dialog = None
        self.thread_pool = QThreadPool()
        self.signals = WorkerSignals()
        self.signals.track_ready.connect(self._on_track_ready)
        self.signals.lyrics_ready.connect(self._on_lyrics_ready)
        self.signals.art_ready.connect(self._on_art_ready)
        self._init_ui()
        self._init_tray()
        
        # Initialize anchors based on starting position
        #self._anchor_center_x = self.x() + self.width() // 2
        #self._anchor_bottom_y = self.y() + self.height()
        #self.resize(self.settings.get("width", DEFAULT_WIDTH), self.settings.get("height", DEFAULT_HEIGHT))
        # 1. Apply the target size FIRST
        target_width = self.settings.get("width", 600)
        target_height = self.settings.get("height", 170)
        self.resize(target_width, target_height)

        # 2. Check if we have saved coordinates
        start_x = self.settings.get("pos_x")
        start_y = self.settings.get("pos_y")
        
        if start_x is not None and start_y is not None:
            self.move(start_x, start_y)
            # Initialize anchors mathematically using the target dimensions
            self._anchor_center_x = start_x + target_width // 2
            self._anchor_bottom_y = start_y + target_height
        else:
            # If no saved location, use your recenter function
            self.recenter()
        self.spotify_timer = QTimer(self)
        self.spotify_timer.timeout.connect(self.poll_spotify)
        self.spotify_timer.start(POLL_INTERVAL_MS)
        
        self.render_timer = QTimer(self)
        self.render_timer.timeout.connect(self.refresh_display)
        self.render_timer.start(RENDER_INTERVAL_MS)
        self.poll_spotify()
        
    def _init_ui(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, self.settings["click_through"])
        
        # Top-level layout is horizontal: [Prev] [Center column] [Next]. The
        # buttons live directly in this row (not nested inside a header row
        # above the lyrics) so they stay vertically centered against the
        # *whole* overlay height as it grows/shrinks - Qt re-centers
        # AlignVCenter items automatically on every resize, no manual
        # position math needed.
        self.main_layout = QHBoxLayout()
        self.main_layout.setContentsMargins(SIDE_MARGIN, MARGIN_TOP_MAX, SIDE_MARGIN, MARGIN_BOTTOM_MAX)
        self.main_layout.setSpacing(10)
        
        # Let the window be resized to any size, including smaller than the
        # layout's "natural" content size - our own _recompute_height /
        # _update_responsive_mode logic decides what to shrink or hide,
        # instead of Qt silently refusing the resize (this is what caused
        # the "Unable to set geometry ... minimum size" warnings/bouncing
        # on Windows).
        self.main_layout.setSizeConstraint(QLayout.SetNoConstraint)
        self.setLayout(self.main_layout)
        self.setMinimumSize(0, 0)
        
        self.btn_prev = QPushButton()
        self.btn_prev.setCursor(Qt.PointingHandCursor)
        self.btn_prev.setFocusPolicy(Qt.NoFocus)
        self.btn_prev.clicked.connect(self.skip_previous)
        
        self.btn_next = QPushButton()
        self.btn_next.setCursor(Qt.PointingHandCursor)
        self.btn_next.setFocusPolicy(Qt.NoFocus)
        self.btn_next.clicked.connect(self.skip_next)
        
        self.main_layout.addWidget(self.btn_prev, 0, Qt.AlignVCenter)
        
        # --- Center column ---
        self.center_container = QWidget()
        self.center_layout = QVBoxLayout(self.center_container)
        self.center_layout.setContentsMargins(0, 0, 0, 0)
        self.center_layout.setSpacing(0)
        
        # Art + title/artist, wrapped in their own widget so we can toggle
        # its alignment (top-left in the normal layout, centered in the
        # compact "art only" layout) with a single setAlignment() call
        # rather than restructuring the layout each time.
        self.identity_widget = QWidget()
        identity_layout = QHBoxLayout(self.identity_widget)
        identity_layout.setContentsMargins(0, 0, 0, 0)
        identity_layout.setSpacing(8)
        
        self.label_art = QLabel("Art")
        self.label_art.setFixedSize(ART_SIZE, ART_SIZE)
        self.label_art.setStyleSheet("background: #333; border-radius: 4px;")
        self.label_art.setAlignment(Qt.AlignCenter)
        
        info_layout = QVBoxLayout()
        info_layout.setSpacing(0)
        self.label_title = QLabel("Not Playing")
        self.label_artist = QLabel("Spotify")
        info_layout.addWidget(self.label_title)
        info_layout.addWidget(self.label_artist)
        
        identity_layout.addWidget(self.label_art, 0, Qt.AlignVCenter)
        identity_layout.addLayout(info_layout)
        identity_layout.setAlignment(info_layout, Qt.AlignVCenter)
        
        self.center_layout.addWidget(self.identity_widget, 0, Qt.AlignLeft | Qt.AlignTop)
        
        self.spacer_top_mid = QWidget()
        self.spacer_top_mid.setFixedHeight(TOP_GAP)
        self.center_layout.addWidget(self.spacer_top_mid)
        
        self.label_current = QLabel("Waiting for Spotify\u2026")
        self.label_current.setAlignment(Qt.AlignCenter)
        self.label_current.setWordWrap(True)
        self.center_layout.addWidget(self.label_current)
        
        self.spacer_mid_bottom = QWidget()
        self.spacer_mid_bottom.setFixedHeight(LYRIC_GAP_MAX)
        self.center_layout.addWidget(self.spacer_mid_bottom)
        
        self.label_next = QLabel("")
        self.label_next.setAlignment(Qt.AlignCenter)
        self.center_layout.addWidget(self.label_next)
        
        self.main_layout.addWidget(self.center_container, 1)
        self.main_layout.addWidget(self.btn_next, 0, Qt.AlignVCenter)
        self._apply_style()

    def _init_tray(self):
        self.tray = QSystemTrayIcon(self)
        icon = self.style().standardIcon(QStyle.SP_MediaVolume)
        self.tray.setIcon(icon)
        
        menu = QMenu()
        settings_action = QAction("Settings...", self)
        settings_action.triggered.connect(self.open_settings)
        menu.addAction(settings_action)

        reconfigure_action = QAction("Reconfigure Spotify...", self)
        reconfigure_action.triggered.connect(self._reconfigure_spotify)
        menu.addAction(reconfigure_action)
        menu.addSeparator()
        
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(QApplication.quit)
        menu.addAction(quit_action)
        
        self.tray.setContextMenu(menu)
        self.tray.show()

    def _reconfigure_spotify(self):
        """For fixing a typo'd Client ID/Secret, or switching accounts,
        without having to know that a hidden credentials file exists."""
        reply = QMessageBox.question(
            self,
            "Reconfigure Spotify",
            "This will sign out and let you re-enter your Spotify Client "
            "ID/Secret. Continue?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        clear_credentials()
        wizard = SetupWizard()
        if wizard.exec_() != QDialog.Accepted:
            return

        try:
            self.spotify = SpotifyClient()
        except Exception as e:
            QMessageBox.critical(self, "Spotify Error", f"Couldn't connect: {e}")
            return

        self.current_track_id = None
        self.lyrics_data = None
        self.poll_spotify()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        bg = QColor(self.settings["bg_color"])
        bg.setAlpha(self.settings["bg_opacity"])
        painter.setBrush(bg)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 18, 18)

    def _make_skip_icon(self, direction, color_hex, size=16):
        # Drawn ourselves (rather than using the OS's standard icon) so the
        # color actually follows the text_color setting - native/standard
        # icons are baked-in and can't be recolored via stylesheets, which
        # is why changing colors previously had no effect on the buttons.
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor(color_hex))
        painter.setPen(Qt.NoPen)
        
        if direction == "prev":
            painter.drawRect(2, 2, 2, size - 4)
            triangle = QPolygon([QPoint(size - 3, 2), QPoint(size - 3, size - 2), QPoint(5, size // 2)])
        else:
            painter.drawRect(size - 4, 2, 2, size - 4)
            triangle = QPolygon([QPoint(3, 2), QPoint(3, size - 2), QPoint(size - 5, size // 2)])
            
        painter.drawPolygon(triangle)
        painter.end()
        return QIcon(pixmap)

    def _apply_style(self):
        font_size = self.settings["font_size"]
        self.label_current.setFont(QFont("Segoe UI", font_size, QFont.Bold))
        self.label_current.setStyleSheet(f"color: {self.settings['text_color']};")
        
        next_color = self.settings.get("next_text_color", "#808080")
        self.label_next.setFont(QFont("Segoe UI", max(10, int(font_size * 0.65))))
        self.label_next.setStyleSheet(f"color: {next_color};")
        
        # Title/artist use their own fixed sizing (independent of the lyric
        # font_size setting) since they now live in a small top-left block.
        self.label_title.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.label_title.setStyleSheet(f"color: {self.settings['text_color']};")
        self.label_artist.setFont(QFont("Segoe UI", 9))
        self.label_artist.setStyleSheet(f"color: {next_color};")
        
        btn_color = self.settings.get("button_color", "#FFFFFF")
        btn_style = "QPushButton { background: transparent; border: none; padding: 5px; } QPushButton:hover { background: rgba(255, 255, 255, 0.1); border-radius: 5px; }"
        self.btn_prev.setStyleSheet(btn_style)
        self.btn_next.setStyleSheet(btn_style)

        self.btn_prev.setIcon(self._make_skip_icon("prev", btn_color))
        self.btn_next.setIcon(self._make_skip_icon("next", btn_color))

    def open_settings(self):
        if self.settings_dialog and self.settings_dialog.isVisible():
            self.settings_dialog.raise_()
        else:
            self.settings_dialog = SettingsDialog(self.settings)
            self.settings_dialog.settings_changed.connect(self.apply_settings)
            self.settings_dialog.recenter_requested.connect(self.recenter)
            self.settings_dialog.show()

    def apply_settings(self, new_settings):
        # Store the old width to check if we need to resize
        old_width = self.settings.get("width")
        self.settings = new_settings
        save_settings(self.settings)
        self._apply_style()
        self.setAttribute(Qt.WA_TransparentForMouseEvents, self.settings["click_through"])
        
        # If the width changed, trigger the resize logic
        if self.settings["width"] != old_width:
            self._resize_preserving_anchor(new_width=self.settings["width"])
        self._recompute_height()
        self.update()

    def recenter(self):
        screen = QApplication.primaryScreen().geometry()
        self._anchor_center_x = screen.width() // 2
        self._anchor_bottom_y = 180 # maybe 200
        self._resize_preserving_anchor()

    def _resize_preserving_anchor(self, new_width=None, new_height=None):
        # Use the width from settings as the ultimate truth if new_width isn't passed
        width = new_width if new_width is not None else self.settings.get("width", self.width())
        height = new_height if new_height is not None else self.height()
        
        # Apply the resize
        self.resize(width, height)
        # Explicitly reposition using the saved anchors
        self.move(self._anchor_center_x - width // 2, self._anchor_bottom_y - height)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_responsive_mode()

    def _update_responsive_mode(self):
        if not hasattr(self, "identity_widget"):
            return
            
        natural_width = self.identity_widget.sizeHint().width()
        compact_threshold = natural_width + ART_INFO_COMPACT_BUFFER
        is_compact = self.center_container.width() < compact_threshold
        
        if is_compact == self._is_compact_mode:
            return
            
        self._is_compact_mode = is_compact
        if is_compact:
            self.center_layout.setAlignment(self.identity_widget, Qt.AlignCenter)
            self.label_current.setVisible(False)
            self.label_next.setVisible(False)
            self.spacer_top_mid.setVisible(False)
            self.spacer_mid_bottom.setVisible(False)
        else:
            self.center_layout.setAlignment(self.identity_widget, Qt.AlignLeft | Qt.AlignTop)
            self.label_current.setVisible(True)
            self.spacer_top_mid.setVisible(True)
            # label_next / spacer_mid_bottom visibility is governed by the
            # vertical squeeze in _recompute_height, not here.
            
        self._recompute_height()

    @staticmethod
    def _eat(deficit, max_val, min_val):
        """Shrinks one margin/gap from its MAX toward its MIN to absorb as
        much of `deficit` as it can, and returns (new_value, leftover_deficit)
        so the next item in the squeeze order can absorb whatever's left."""
        room = max_val - min_val
        take = min(deficit, room)
        return max_val - take, deficit - take

    def _recompute_height(self):
        target_height = self.settings.get("height", DEFAULT_HEIGHT)

        if self._is_compact_mode:
            self.label_current.setVisible(False)
            self.label_next.setVisible(False)
            self.spacer_top_mid.setVisible(False)
            self.spacer_mid_bottom.setVisible(False)

            id_h = self.identity_widget.sizeHint().height()
            max_needed = id_h + MARGIN_TOP_MAX + MARGIN_BOTTOM_MAX
            min_needed = id_h + MARGIN_TOP_MIN + MARGIN_BOTTOM_MIN

            if target_height >= max_needed:
                top_m, bottom_m = MARGIN_TOP_MAX, MARGIN_BOTTOM_MAX
                min_h = target_height
            elif target_height >= min_needed:
                deficit = max_needed - target_height
                bottom_m, deficit = self._eat(deficit, MARGIN_BOTTOM_MAX, MARGIN_BOTTOM_MIN)
                top_m, deficit = self._eat(deficit, MARGIN_TOP_MAX, MARGIN_TOP_MIN)
                min_h = target_height
            else:
                # Can't shrink further without clipping the art/title row -
                # grow to fit instead of clipping it.
                top_m, bottom_m = MARGIN_TOP_MIN, MARGIN_BOTTOM_MIN
                min_h = min_needed

            self.main_layout.setContentsMargins(SIDE_MARGIN, top_m, SIDE_MARGIN, bottom_m)
        else:
            self.label_current.setVisible(True)
            self.spacer_top_mid.setVisible(True)

            id_h = self.identity_widget.sizeHint().height()
            cur_h = self.label_current.sizeHint().height()
            next_h = self.label_next.sizeHint().height()

            def needed(show_next, top_m, bottom_m, gap, top_gap):
                total = top_m + id_h + top_gap + cur_h + bottom_m
                if show_next:
                    total += gap + next_h
                return total

            max_with_next = needed(True, MARGIN_TOP_MAX, MARGIN_BOTTOM_MAX, LYRIC_GAP_MAX, TOP_GAP_MAX)
            min_with_next = needed(True, MARGIN_TOP_MIN, MARGIN_BOTTOM_MIN, LYRIC_GAP_MIN, TOP_GAP_MIN)
            max_no_next = needed(False, MARGIN_TOP_MAX, MARGIN_BOTTOM_MAX, LYRIC_GAP_MAX, TOP_GAP_MAX)
            min_no_next = needed(False, MARGIN_TOP_MIN, MARGIN_BOTTOM_MIN, LYRIC_GAP_MIN, TOP_GAP_MIN)

            if target_height >= max_with_next:
                # Roomy - use the comfortable defaults.
                top_m, bottom_m, gap, top_gap = MARGIN_TOP_MAX, MARGIN_BOTTOM_MAX, LYRIC_GAP_MAX, TOP_GAP_MAX
                show_next = True
                min_h = target_height
            elif target_height >= min_with_next:
                # Squeeze in priority order: bottom margin -> lyric gap ->
                # art/lyric gap -> top margin, until the deficit is absorbed.
                deficit = max_with_next - target_height
                bottom_m, deficit = self._eat(deficit, MARGIN_BOTTOM_MAX, MARGIN_BOTTOM_MIN)
                gap, deficit = self._eat(deficit, LYRIC_GAP_MAX, LYRIC_GAP_MIN)
                top_gap, deficit = self._eat(deficit, TOP_GAP_MAX, TOP_GAP_MIN)
                top_m, deficit = self._eat(deficit, MARGIN_TOP_MAX, MARGIN_TOP_MIN)
                show_next = True
                min_h = target_height
            elif target_height >= max_no_next:
                # Even fully squeezed there's no room for the next-line
                # preview at a comfortable size - drop it and go back to
                # comfortable margins for just the current line.
                top_m, bottom_m, gap, top_gap = MARGIN_TOP_MAX, MARGIN_BOTTOM_MAX, LYRIC_GAP_MAX, TOP_GAP_MAX
                show_next = False
                min_h = target_height
            elif target_height >= min_no_next:
                deficit = max_no_next - target_height
                bottom_m, deficit = self._eat(deficit, MARGIN_BOTTOM_MAX, MARGIN_BOTTOM_MIN)
                top_gap, deficit = self._eat(deficit, TOP_GAP_MAX, TOP_GAP_MIN)
                top_m, deficit = self._eat(deficit, MARGIN_TOP_MAX, MARGIN_TOP_MIN)
                gap = LYRIC_GAP_MIN
                show_next = False
                min_h = target_height
            else:
                # Can't shrink further without clipping the current lyric
                # line - grow to fit instead of clipping it.
                top_m, bottom_m, gap, top_gap = MARGIN_TOP_MIN, MARGIN_BOTTOM_MIN, LYRIC_GAP_MIN, TOP_GAP_MIN
                show_next = False
                min_h = min_no_next

            self.main_layout.setContentsMargins(SIDE_MARGIN, top_m, SIDE_MARGIN, bottom_m)
            self.spacer_top_mid.setFixedHeight(top_gap)
            self.spacer_top_mid.setVisible(True)
            self.spacer_mid_bottom.setFixedHeight(gap)
            self.spacer_mid_bottom.setVisible(show_next)
            self.label_next.setVisible(show_next)

        # Tell Qt our real floor for this state, then sync the actual window
        # to it (this can grow OR shrink us back - e.g. after being forced
        # taller to avoid clipping, a bigger target_height should let us
        # shrink back down again).
        self.setMinimumHeight(min_h)
        if self.height() != min_h:
            self._resize_preserving_anchor(new_height=min_h)
    def _set_elided_text(self, label, text):
        metrics = label.fontMetrics()
        # Available width is the center column's width, not the full
        # overlay width, since Prev/Next live outside it.
        available_width = self.center_container.width() - 16
        label.setText(metrics.elidedText(text, Qt.ElideRight, max(available_width, 20)))

    def skip_previous(self):
        self.thread_pool.start(Worker(self._skip_bg, self.spotify.previous_track))

    def skip_next(self):
        self.thread_pool.start(Worker(self._skip_bg, self.spotify.next_track))

    def _skip_bg(self, spotify_fn):
        # Runs entirely on a background thread: send the skip, then poll
        # Spotify repeatedly (starting fast, backing off) until it actually
        # reports the new track - Spotify's API doesn't register a skip on
        # a fixed schedule, so a single wait-then-check either feels slow
        # (if we waited longer than needed) or misses it (if we didn't wait
        # long enough). None of this blocks the UI.
        previous_id = self.current_track_id
        spotify_fn()

        track = None
        delay = 0.15
        deadline = time.monotonic() + 2.5
        while time.monotonic() < deadline:
            time.sleep(delay)
            try:
                track = self.spotify.get_current_track()
            except Exception as e:
                print(f"[spotify] Error polling after skip: {e}")
                break
            if track and track["id"] != previous_id:
                break
            delay = min(delay * 1.5, 0.5)

        self.signals.track_ready.emit(track)

    def poll_spotify(self):
        self.thread_pool.start(Worker(self._poll_bg))

    def _poll_bg(self):
        track = None
        try:
            track = self.spotify.get_current_track()
        except Exception as e:
            print(f"[spotify] Error polling: {e}")
        self.signals.track_ready.emit(track)

    def _on_track_ready(self, track):
        # Runs on the main/UI thread (Qt queues signals back across
        # threads automatically), so it's safe to touch widgets here.
        self.last_track = track
        if not track:
            self.current_track_id = None
            return
            
        if track["id"] != self.current_track_id:
            self.current_track_id = track["id"]
            self.lyrics_data = None
            track_id = track["id"]
            self.thread_pool.start(Worker(
                self._fetch_lyrics_bg, track["title"], track["artist"],
                track["album"], track["duration_ms"], track_id,
            ))
            # NOTE: "album_art_url" must match the key spotify_client.py's
            # get_current_track() returns - if you rename one, rename both.
            self.thread_pool.start(Worker(self._fetch_art_bg, track.get("album_art_url"), track_id))
            
        self.synced_progress_ms = track["progress_ms"]
        self.synced_at = time.monotonic()
        self.is_playing = track["is_playing"]

    def _fetch_lyrics_bg(self, title, artist, album, duration_ms, track_id):
        data = fetch_lyrics(title, artist, album, duration_ms)
        self.signals.lyrics_ready.emit(track_id, data)

    def _on_lyrics_ready(self, track_id, data):
        if track_id != self.current_track_id:
            return  # stale result for a track we've since skipped past
        self.lyrics_data = data

    def _fetch_art_bg(self, url, track_id):
        image = None
        if url:
            try:
                resp = requests.get(url, timeout=5)
                if resp.status_code == 200:
                    img = QImage()
                    if img.loadFromData(resp.content):
                        image = img
            except Exception as e:
                print(f"[art] failed to fetch album art: {e}")
                
        # NOTE: QPixmap must only be touched on the main/GUI thread, so we
        # hand off a QImage (which is thread-safe) and convert it to a
        # QPixmap in the main-thread slot below.
        self.signals.art_ready.emit(track_id, image)

    def _on_art_ready(self, track_id, image):
        if track_id != self.current_track_id:
            return  # stale result for a track we've since skipped past
            
        if image is not None and not image.isNull():
            scaled = QPixmap.fromImage(image).scaled(
                ART_SIZE, ART_SIZE, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
            )
            x = max(0, (scaled.width() - ART_SIZE) // 2)
            y = max(0, (scaled.height() - ART_SIZE) // 2)
            self.label_art.setPixmap(scaled.copy(x, y, ART_SIZE, ART_SIZE))
            self.label_art.setText("")
        else:
            self.label_art.setPixmap(QPixmap())
            self.label_art.setText("Art")

    def refresh_display(self):
        track = self.last_track
        if not track:
            self.label_current.setText("Nothing playing")
            self.label_next.setText("")
            self._recompute_height()
            return
            
        self.label_title.setText(track['title'])
        self.label_artist.setText(track['artist'])
        
        if not self.lyrics_data:
            self.label_current.setText(f"{track['title']} \u2014 {track['artist']}")
            self.label_next.setText("")
            self._recompute_height()
            return
            
        # Handle plain lyrics
        if self.lyrics_data.get("type") == "plain":
            self.label_current.setText("Lyrics unsynced")
            self.label_next.setText("")  # Clear the next line
            self._recompute_height()
            return
            
        elapsed_ms = (time.monotonic() - self.synced_at) * 1000
        progress_sec = (self.synced_progress_ms + elapsed_ms + self.settings["sync_offset_ms"]) / 1000
        lines = self.lyrics_data.get("lines", [])
        current_line, next_line = "", ""
        
        for i, (ts, text) in enumerate(lines):
            if ts <= progress_sec:
                current_line = text
                next_line = lines[i + 1][1] if i + 1 < len(lines) else ""
            else:
                break
                
        self.label_current.setText(current_line or "\u266a")
        self._set_elided_text(self.label_next, next_line)
        self._recompute_height()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.drag_pos:
            self.move(event.globalPos() - self.drag_pos)
            self._anchor_center_x = self.x() + self.width() // 2
            self._anchor_bottom_y = self.y() + self.height()
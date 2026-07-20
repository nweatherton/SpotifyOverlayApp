# settings_dialog.py
#
# The "GUI mode" reachable from the tray icon: lets you tweak colors, size,
# opacity, and a few other display options, with changes applied live.

from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QPushButton,
    QSlider,
    QSpinBox,
    QCheckBox,
    QColorDialog,
    QLabel,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor

from settings import DEFAULTS


class SettingsDialog(QDialog):
    # Emitted with the full settings dict every time something changes,
    # so the overlay can apply it immediately.
    settings_changed = pyqtSignal(dict)
    # Emitted when the user clicks "Center overlay".
    recenter_requested = pyqtSignal()

    def __init__(self, current_settings, parent=None):
        super().__init__(parent)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint) # Get rid of question mark
        self.setWindowTitle("Lyrics Overlay Settings")
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.setMinimumWidth(340)

        self.settings = current_settings.copy()
        self._color_buttons = {}

        root = QVBoxLayout(self)
        form = QFormLayout()
        form.setSpacing(10)

        # --- Width ---
        self.width_spin = QSpinBox()
        self.width_spin.setRange(80, 1600)
        self.width_spin.setSingleStep(20)
        self.width_spin.setValue(self.settings["width"])
        self.width_spin.valueChanged.connect(self._emit_change)
        form.addRow("Overlay width:", self.width_spin)

        # --- Height ---
        self.height_spin = QSpinBox()
        self.height_spin.setRange(16, 500)
        self.height_spin.setSingleStep(10)
        self.height_spin.setValue(self.settings["height"])
        self.height_spin.valueChanged.connect(self._emit_change)
        form.addRow("Height:", self.height_spin)

        # --- Font size ---
        self.font_spin = QSpinBox()
        self.font_spin.setRange(10, 48)
        self.font_spin.setValue(self.settings["font_size"])
        self.font_spin.valueChanged.connect(self._emit_change)
        form.addRow("Font size:", self.font_spin)

        # --- Background opacity ---
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(0, 255)
        self.opacity_slider.setValue(self.settings["bg_opacity"])
        self.opacity_slider.valueChanged.connect(self._emit_change)
        form.addRow("Background opacity:", self.opacity_slider)

        # --- Sync offset ---
        self.offset_spin = QSpinBox()
        self.offset_spin.setRange(-3000, 3000)
        self.offset_spin.setSingleStep(50)
        self.offset_spin.setSuffix(" ms")
        self.offset_spin.setValue(self.settings["sync_offset_ms"])
        self.offset_spin.valueChanged.connect(self._emit_change)
        form.addRow("Lyric sync offset:", self.offset_spin)

        # --- Click-through ---
        self.click_through_check = QCheckBox("Let clicks pass through to what's underneath")
        self.click_through_check.setChecked(self.settings["click_through"])
        self.click_through_check.stateChanged.connect(self._emit_change)
        form.addRow(self.click_through_check)

        root.addLayout(form)

        # --- Colors ---
        color_row = QHBoxLayout()
        color_row.addWidget(self._make_color_button("Text", "text_color"))
        color_row.addWidget(self._make_color_button("Next line", "next_text_color"))
        color_row.addWidget(self._make_color_button("Background", "bg_color"))
        color_row.addWidget(self._make_color_button("Buttons", "button_color"))
        root.addLayout(color_row)

        note = QLabel(
            "Tip: while click-through is on, drag/quit from this window\n"
            "or the tray icon, since you can't click the overlay itself."
        )
        note.setStyleSheet("color: gray; font-size: 11px;")
        root.addWidget(note)

        # --- Bottom buttons ---
        btn_row = QHBoxLayout()
        recenter_btn = QPushButton("Center overlay")
        recenter_btn.clicked.connect(self.recenter_requested.emit)
        reset_btn = QPushButton("Reset to defaults")
        reset_btn.clicked.connect(self._reset_defaults)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)

        btn_row.addWidget(recenter_btn)
        btn_row.addWidget(reset_btn)
        btn_row.addStretch()
        btn_row.addWidget(close_btn)
        root.addLayout(btn_row)

    # ---------- helpers ----------

    def _make_color_button(self, label, key):
        btn = QPushButton(label)
        self._color_buttons[key] = btn
        self._paint_button(btn, self.settings[key])

        def pick():
            chosen = QColorDialog.getColor(QColor(self.settings[key]), self, f"Choose {label} color")
            if chosen.isValid():
                self.settings[key] = chosen.name()
                self._paint_button(btn, chosen.name())
                self._emit_change()

        btn.clicked.connect(pick)
        return btn

    @staticmethod
    def _paint_button(btn, hex_color):
        text_color = "#000000" if QColor(hex_color).lightness() > 140 else "#FFFFFF"
        btn.setStyleSheet(
            f"background-color: {hex_color}; color: {text_color}; padding: 6px;"
        )

    def _emit_change(self, *_args):
        self.settings["width"] = self.width_spin.value()
        self.settings["height"] = self.height_spin.value()
        self.settings["font_size"] = self.font_spin.value()
        self.settings["bg_opacity"] = self.opacity_slider.value()
        self.settings["sync_offset_ms"] = self.offset_spin.value()
        self.settings["click_through"] = self.click_through_check.isChecked()
        self.settings_changed.emit(self.settings.copy())

    def _reset_defaults(self):
        self.settings = DEFAULTS.copy()
        self.width_spin.setValue(self.settings["width"])
        self.height_spin.setValue(self.settings["height"]) # NOAH ADDED
        self.font_spin.setValue(self.settings["font_size"])
        self.opacity_slider.setValue(self.settings["bg_opacity"])
        self.offset_spin.setValue(self.settings["sync_offset_ms"])
        self.click_through_check.setChecked(self.settings["click_through"])
        for key, btn in self._color_buttons.items():
            self._paint_button(btn, self.settings[key])
        self._emit_change()
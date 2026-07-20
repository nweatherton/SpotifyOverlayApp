# setup_wizard.py
#
# Shown the first time the app runs (or whenever there are no saved Spotify
# credentials): walks a non-technical user through creating a free Spotify
# "app" - Spotify requires every program that talks to their API to have
# one, there's no way around it - and saves what they enter locally so they
# never have to do this again on this computer.

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QLabel,
    QPushButton, QHBoxLayout, QMessageBox
)

from app_config import save_credentials, REDIRECT_URI

DASHBOARD_URL = "https://developer.spotify.com/dashboard"


class SetupWizard(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Spotify Lyrics Overlay - First-Time Setup")
        self.setMinimumWidth(500)

        root = QVBoxLayout(self)

        intro = QLabel(
            "This app needs a free Spotify \u201capp\u201d so Spotify will let it see "
            "what you're playing. It's Spotify's requirement, not a purchase or "
            "a subscription - it takes about 2 minutes, one time only."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        steps = QLabel(
            "1. Open the link below and log in with your Spotify account.\n"
            "2. Click \u201cCreate app.\u201d\n"
            "3. App name / description: anything you like.\n"
            "4. Redirect URI: paste in exactly this, then click \u201cAdd\u201d:\n"
            f"      {REDIRECT_URI}\n"
            "5. Check the \u201cWeb API\u201d box and save.\n"
            "6. Open the app you just created, click \u201cSettings,\u201d and copy\n"
            "   the Client ID and Client Secret into the boxes below."
        )
        steps.setWordWrap(True)
        steps.setStyleSheet(
            "color: #222; background: #f2f2f2; padding: 10px; border-radius: 6px;"
        )
        root.addWidget(steps)

        link = QLabel(f'<a href="{DASHBOARD_URL}">Open the Spotify Developer Dashboard</a>')
        link.setOpenExternalLinks(True)
        root.addWidget(link)

        form = QFormLayout()
        form.setSpacing(8)

        self.client_id_edit = QLineEdit()
        self.client_id_edit.setPlaceholderText("Paste your Client ID here")
        form.addRow("Client ID:", self.client_id_edit)

        secret_row = QHBoxLayout()
        self.client_secret_edit = QLineEdit()
        self.client_secret_edit.setPlaceholderText("Paste your Client Secret here")
        self.client_secret_edit.setEchoMode(QLineEdit.Password)
        secret_row.addWidget(self.client_secret_edit)

        self.show_btn = QPushButton("Show")
        self.show_btn.setCheckable(True)
        self.show_btn.setFixedWidth(56)
        self.show_btn.toggled.connect(self._toggle_secret_visibility)
        secret_row.addWidget(self.show_btn)

        form.addRow("Client Secret:", secret_row)
        root.addLayout(form)

        note = QLabel(
            "Your Client ID/Secret are saved only on this computer and are sent "
            "only to Spotify - never anywhere else. Please look in the taskbar's "
            "system tray and right click to get options and information about the overlay."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: gray; font-size: 11px;")
        root.addWidget(note)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        quit_btn = QPushButton("Quit")
        quit_btn.clicked.connect(self.reject)
        save_btn = QPushButton("Save && Continue")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(quit_btn)
        btn_row.addWidget(save_btn)
        root.addLayout(btn_row)

    def _toggle_secret_visibility(self, checked):
        self.client_secret_edit.setEchoMode(QLineEdit.Normal if checked else QLineEdit.Password)
        self.show_btn.setText("Hide" if checked else "Show")

    def _on_save(self):
        client_id = self.client_id_edit.text().strip()
        client_secret = self.client_secret_edit.text().strip()
        if not client_id or not client_secret:
            QMessageBox.warning(
                self, "Missing info",
                "Please fill in both the Client ID and Client Secret."
            )
            return
        save_credentials(client_id, client_secret)
        self.accept()

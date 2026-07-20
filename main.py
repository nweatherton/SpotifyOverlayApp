# main.py
#
# Entry point. Run this with: python main.py (or double-click the built exe)

import sys
from PyQt5.QtWidgets import QApplication, QDialog, QMessageBox
from PyQt5.QtGui import QIcon
from app_config import has_credentials, resource_path
from setup_wizard import SetupWizard



def main():
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(resource_path("app_icon.ico")))
    app.setQuitOnLastWindowClosed(False)
    
    if not has_credentials():
        wizard = SetupWizard()
        if wizard.exec_() != QDialog.Accepted:
            return  # user closed/quit out of setup - nothing more to do

    # Imported here, after setup, so a plain "no credentials yet" case never
    # has to touch Spotify/network code at all.
    from overlay import LyricsOverlay

    try:
        overlay = LyricsOverlay()
    except Exception as e:
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setWindowTitle("Couldn't start")
        msg_box.setText("Something went wrong connecting to Spotify:\n\n"
                        f"{e}\n\n"
                        "Double check the Client ID/Secret and that the Redirect URI in "
                        "your Spotify app's settings is exactly:\n"
                        "http://127.0.0.1:8888/callback")
        
        # This is the magic line that makes the text selectable
        msg_box.setTextInteractionFlags(Qt.TextSelectableByMouse)
        
        msg_box.exec_()
        return

    overlay.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

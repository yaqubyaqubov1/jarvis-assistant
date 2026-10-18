import sys

from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow


def main():

    app = QApplication(
        sys.argv
    )

    app.setApplicationName(
        "JARVIS"
    )

    app.setOrganizationName(
        "JARVIS"
    )

    # Prevent the application from closing
    # merely because the main window is hidden.
    app.setQuitOnLastWindowClosed(
        False
    )

    window = MainWindow()

    window.show()

    sys.exit(
        app.exec()
    )


if __name__ == "__main__":
    main()
import sys

from PySide6.QtWidgets import QApplication

from bpm_light_mapper.app.ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()

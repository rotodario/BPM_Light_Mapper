import sys

from PySide6.QtWidgets import QApplication

from bpm_light_mapper.app.ui.main_window import MainWindow
from bpm_light_mapper.app.ui.theme import apply_theme
from bpm_light_mapper.app.utils.logging_utils import get_logger, install_exception_hooks, setup_logging


def main() -> int:
    setup_logging()
    install_exception_hooks()
    logger = get_logger("main")
    logger.info("Starting BPM Light Mapper")
    app = QApplication(sys.argv)
    apply_theme(app)
    window = MainWindow()
    window.show()
    exit_code = app.exec()
    logger.info("Application exited with code %s", exit_code)
    return exit_code

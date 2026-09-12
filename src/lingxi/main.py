from __future__ import annotations

import os
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from .main_window import MainWindow


def main() -> int:
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
    app = QApplication(sys.argv)
    app.setApplicationName("灵析 X1")
    app.setOrganizationName("Lingxi Lab")
    app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    window = MainWindow(start_simulator=True)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

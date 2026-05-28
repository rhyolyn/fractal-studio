from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from fractal_studio.main_window_factory import create_main_window


def main() -> int:
    application = QApplication(sys.argv)
    window = create_main_window()
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())

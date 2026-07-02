"""Корневой запускатель (используется PyInstaller как входной скрипт).

Запуск из исходников:  python main.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from funpay_assistant.app import main  # noqa: E402

if __name__ == "__main__":
    main()

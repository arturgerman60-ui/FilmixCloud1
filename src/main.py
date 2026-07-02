"""FunPay AutoResponder — application entry point.

Bootstraps environment/logging, installs a global crash guard, then launches
the CustomTkinter UI. Designed to be the PyInstaller entry script as well.
"""
from __future__ import annotations

import os
import sys
import traceback


def _bootstrap_path() -> None:
    """Ensure ``src`` package is importable both from source and when frozen."""
    here = os.path.dirname(os.path.abspath(__file__))
    parent = os.path.dirname(here)
    for path in (parent, here):
        if path not in sys.path:
            sys.path.insert(0, path)


def _load_env() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except Exception:
        pass


def main() -> int:
    _bootstrap_path()
    _load_env()

    try:
        from src.utils.logger import get_logger, setup_logging
    except ModuleNotFoundError:
        # When launched as ``python src/main.py`` without package context.
        from utils.logger import get_logger, setup_logging  # type: ignore

    setup_logging()
    log = get_logger("main")
    log.info("=" * 60)
    log.info("Starting FunPay AutoResponder")

    def _excepthook(exc_type, exc_value, exc_tb):
        log.critical("Unhandled exception:\n%s",
                     "".join(traceback.format_exception(exc_type, exc_value,
                                                        exc_tb)))

    sys.excepthook = _excepthook

    try:
        try:
            from src.ui.app import run_app
        except ModuleNotFoundError:
            from ui.app import run_app  # type: ignore
        run_app()
        return 0
    except Exception as exc:  # pragma: no cover
        log.critical("Fatal error during startup: %s", exc, exc_info=True)
        try:
            import tkinter.messagebox as mb

            mb.showerror("FunPay AutoResponder",
                         f"Fatal error:\n{exc}\n\nSee logs for details.")
        except Exception:
            print(f"Fatal error: {exc}")
        return 1
    finally:
        log.info("Application exited.")


if __name__ == "__main__":
    sys.exit(main())

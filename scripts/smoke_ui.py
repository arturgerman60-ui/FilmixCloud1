"""Headless GUI smoke test (run under Xvfb).

Builds the main window, cycles through every tab, opens the rule/template
editors, starts the engine in demo mode briefly, then tears everything down.
Verifies the whole UI constructs without exceptions on a virtual display.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.logger import setup_logging, get_logger  # noqa: E402
from src.utils.config import get_config  # noqa: E402
from src.ui import theme  # noqa: E402


def main() -> int:
    setup_logging("INFO")
    log = get_logger("smoke_ui")
    cfg = get_config()
    theme.init_theme(cfg.get("theme", "dark"), cfg.get("color_theme"))

    from src.ui.app import MainWindow

    app = MainWindow()

    steps = ["dashboard", "rules", "templates", "stats", "logs", "settings"]
    state = {"i": 0}

    def cycle() -> None:
        if state["i"] < len(steps):
            tab = steps[state["i"]]
            log.info("Selecting tab: %s", tab)
            app.select_tab(tab)
            state["i"] += 1
            app.after(150, cycle)
        else:
            log.info("Opening rule editor + template editor")
            app.tabs["rules"].open_editor()
            app.tabs["templates"].open_editor()
            app.after(200, finish)

    def finish() -> None:
        log.info("Starting engine (demo) briefly")
        app.engine.start(force_mock=True)
        app.after(1500, teardown)

    def teardown() -> None:
        log.info("Tearing down")
        try:
            app.engine.shutdown()
            app.tray.stop()
        except Exception:
            pass
        app.destroy()
        print("SMOKE UI: OK")

    app.after(200, cycle)
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

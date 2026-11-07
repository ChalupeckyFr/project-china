"""Hlavní vstupní bod aplikace AbstractView (spouštěný přímo i z abstractview.exe)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Skryjeme uvítací výpis Pygame v konzoli
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")


def _configure_paths() -> None:
    if getattr(sys, "frozen", False):
        bundle_dir = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        src_dir = bundle_dir / "src"
        if src_dir.exists() and str(src_dir) not in sys.path:
            sys.path.insert(0, str(src_dir))
    else:
        repo_root = Path(__file__).resolve().parent.parent
        src_dir = repo_root / "src"
        if str(repo_root) not in sys.path:
            sys.path.insert(0, str(repo_root))
        if src_dir.exists() and str(src_dir) not in sys.path:
            sys.path.insert(0, str(src_dir))


_configure_paths()

from abstractview_app.ui import AbstractViewApp


def main(argv: list[str] | None = None) -> None:
    args = sys.argv[1:] if argv is None else argv
    app = AbstractViewApp()
    if "--self-test" in args:
        out = app.open_output_window()
        out.render_tick(100.0, 16.0)
        app.select_effect("rings")
        out.render_tick(200.0, 16.0)
        app.select_effect("stars")
        app.root.after(250, app.shutdown)
    app.run()


if __name__ == "__main__":
    main()

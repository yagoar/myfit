"""Launcher for the body-scan GUI. All real logic lives in
``body_scanner.gui``; this file just parses CLI flags and starts Flask.

Run::

    .venv/bin/python scripts/scan_gui.py [--port 8060] [--no-open]

Implementation note: pyenv 3.12 on macOS ships without ``_tkinter`` and
the system Tk is from 2010, so a localhost Flask page replaced the
original tkinter prototype. See the body_scanner.gui module for the
app factory.
"""
from __future__ import annotations

import argparse
import threading
import webbrowser

from body_scanner.gui import create_app


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--port", type=int, default=8060)
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--no-open", action="store_true",
                   help="Don't auto-open a browser tab on startup.")
    args = p.parse_args()

    url = f"http://{args.host}:{args.port}/"
    if not args.no_open:
        threading.Timer(0.7, lambda: webbrowser.open(url)).start()
    print(f"MyFit Scan GUI → {url}")
    app = create_app()
    app.run(host=args.host, port=args.port, debug=False, threaded=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

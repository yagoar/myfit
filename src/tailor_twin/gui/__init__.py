"""Body-scan GUI: localhost Flask front-end for ``tailor_twin.scan``.

Public entry points:

* :func:`create_app` — build the Flask app (used by tests).
* :func:`serve`      — launch the dev server + optional browser open.
  Wired into the ``tailor-twin gui`` Typer command.

Routes, runner state and the form helpers live in dedicated submodules
so they're individually testable. The HTML template, CSS, JS and
favicon are served from ``static/`` and ``templates/`` next to this
package.
"""
from __future__ import annotations

import threading
import webbrowser

from .app import create_app

__all__ = ["create_app", "serve"]


def serve(host: str = "127.0.0.1", port: int = 8060,
          open_browser: bool = True) -> int:
    """Run the Flask dev server; optionally open the browser."""
    url = f"http://{host}:{port}/"
    if open_browser:
        threading.Timer(0.7, lambda: webbrowser.open(url)).start()
    print(f"TailorTwin GUI → {url}")
    app = create_app()
    app.run(host=host, port=port, debug=False, threaded=True)
    return 0

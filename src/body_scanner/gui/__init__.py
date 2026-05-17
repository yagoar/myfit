"""Body-scan GUI: localhost Flask front-end for ``scripts/run_scan.py``.

Public entry point: :func:`create_app`. Routes, runner state and the
form helpers live in dedicated submodules so they're individually
testable. The HTML template, CSS, JS and favicon are served from
``static/`` and ``templates/`` next to this package.
"""
from .app import create_app

__all__ = ["create_app"]

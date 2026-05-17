"""Flask app factory + route handlers for the body-scan GUI."""
from __future__ import annotations

import datetime as dt
import json
import queue
from typing import Any

from flask import Flask, Response, jsonify, render_template, request

from .config import (
    DEFAULT_CAPTURES_DIR,
    DEFAULT_RESULTS_DIR,
    PATTERN_SYSTEMS,
    REPO_ROOT,
    WAIST_COLORS,
)
from .forms import build_cmd, validate
from .runner import Runner


def create_app(runner: Runner | None = None) -> Flask:
    """Build the Flask app. Pass ``runner`` for tests; otherwise a fresh
    :class:`Runner` rooted at the repo is created."""
    app = Flask(__name__)  # uses templates/ and static/ next to this module.
    app.config["RUNNER"] = runner or Runner(cwd=REPO_ROOT)

    @app.get("/")
    def index() -> str:
        return render_template(
            "index.html",
            today=dt.date.today().isoformat(),
            colors=WAIST_COLORS,
            systems=PATTERN_SYSTEMS,
            default_captures=str(DEFAULT_CAPTURES_DIR),
            default_results=str(DEFAULT_RESULTS_DIR),
        )

    @app.post("/run")
    def run() -> Any:
        form = request.form.to_dict(flat=True)
        err = validate(form)
        if err:
            return jsonify(ok=False, error=err)
        cmd = build_cmd(form)
        try:
            app.config["RUNNER"].start(cmd)
        except RuntimeError as e:
            return jsonify(ok=False, error=str(e))
        return jsonify(ok=True)

    @app.post("/cancel")
    def cancel() -> Any:
        app.config["RUNNER"].cancel()
        return jsonify(ok=True)

    @app.get("/stream")
    def stream() -> Response:
        runner = app.config["RUNNER"]

        def gen():
            while True:
                try:
                    msg = runner.q.get(timeout=0.5)
                except queue.Empty:
                    # Keep connection alive while waiting for output.
                    if not runner.is_running():
                        yield f"data: {json.dumps({'done': True, 'rc': -1})}\n\n"
                        return
                    yield ": keepalive\n\n"
                    continue
                yield f"data: {json.dumps(msg)}\n\n"
                if msg.get("done"):
                    return

        return Response(
            gen(), mimetype="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    return app

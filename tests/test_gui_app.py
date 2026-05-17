"""Smoke tests for the Flask app: routes return expected shapes."""
from __future__ import annotations

from pathlib import Path

import pytest

from body_scanner.gui.app import create_app
from body_scanner.gui.runner import Runner


@pytest.fixture()
def app(tmp_path: Path):
    a = create_app(runner=Runner(cwd=tmp_path))
    a.config["TESTING"] = True
    return a


@pytest.fixture()
def client(app):
    return app.test_client()


def test_index_renders(client) -> None:
    r = client.get("/")
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert "MyFit" in body
    assert 'id="form"' in body
    assert "favicon.svg" in body
    assert "styles.css" in body
    assert "scan.js" in body


def test_favicon_served(client) -> None:
    r = client.get("/static/favicon.svg")
    assert r.status_code == 200
    assert r.mimetype.startswith("image/svg")


def test_run_rejects_missing_capture(client) -> None:
    r = client.post("/run", data={"person": "Y", "out_prefix": "/tmp/p",
                                   "csv": "on"})
    assert r.status_code == 200
    j = r.get_json()
    assert j["ok"] is False
    assert "capture" in j["error"].lower()


def test_run_rejects_unknown_system(client, tmp_path: Path) -> None:
    r = client.post("/run", data={
        "capture": str(tmp_path), "person": "Y",
        "out_prefix": str(tmp_path / "p"),
        "csv": "on", "system": "burda",
    })
    j = r.get_json()
    assert j["ok"] is False
    assert "system" in j["error"].lower()


def test_cancel_idle_returns_ok(client) -> None:
    r = client.post("/cancel")
    assert r.get_json() == {"ok": True}

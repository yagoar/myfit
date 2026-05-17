"""Unit tests for ``body_scanner.gui.forms`` and the Runner state machine."""
from __future__ import annotations

import time
from pathlib import Path

import pytest

from body_scanner.gui.config import PIPELINE_PY, RUN_SCAN
from body_scanner.gui.forms import (
    build_cmd,
    slugify,
    split_person_name,
    validate,
)
from body_scanner.gui.runner import Runner


# ---------------------------------------------------------------------------
# slugify
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name, expected", [
    ("Yaiza Gómez", "yaiza_g_mez"),
    ("Hello World", "hello_world"),
    ("  trim  me  ", "trim_me"),
    ("---weird-/?chars!!!", "weird_chars"),
    ("", "scan"),
    ("   ", "scan"),
    ("ALL CAPS", "all_caps"),
    ("a1b2", "a1b2"),
])
def test_slugify(name: str, expected: str) -> None:
    assert slugify(name) == expected


# ---------------------------------------------------------------------------
# split_person_name
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("person, expected", [
    ("", ("", "")),
    ("Yaiza", ("Yaiza", "")),
    ("Yaiza Gomez", ("Yaiza", "Gomez")),
    ("Yaiza Maria Gomez Perez", ("Yaiza", "Maria Gomez Perez")),
    ("   Yaiza   Gomez   ", ("Yaiza", "Gomez")),
])
def test_split_person_name(person: str, expected: tuple[str, str]) -> None:
    assert split_person_name(person) == expected


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------


def _good(tmp_path: Path, **overrides) -> dict[str, str]:
    base: dict[str, str] = {
        "capture": str(tmp_path),
        "person": "Yaiza",
        "out_prefix": str(tmp_path / "yaiza_20260517"),
        "csv": "on",
        "obj": "on",
        "smis": "on",
        "system": "aldrich",
        "color": "none",
        "birthday": "1990-05-17",
        "scan_date": "2026-05-17",
    }
    base.update(overrides)
    return base


def test_validate_happy_path(tmp_path: Path) -> None:
    assert validate(_good(tmp_path)) is None


def test_validate_missing_capture(tmp_path: Path) -> None:
    err = validate(_good(tmp_path, capture=""))
    assert err and "capture folder" in err.lower()


def test_validate_nonexistent_capture(tmp_path: Path) -> None:
    err = validate(_good(tmp_path, capture=str(tmp_path / "nope")))
    assert err and "does not exist" in err


def test_validate_missing_person(tmp_path: Path) -> None:
    err = validate(_good(tmp_path, person=""))
    assert err and "person" in err.lower()


def test_validate_no_export(tmp_path: Path) -> None:
    err = validate(_good(tmp_path, csv="", obj="", smis=""))
    assert err and "export" in err.lower()


def test_validate_bad_color(tmp_path: Path) -> None:
    err = validate(_good(tmp_path, color="hotpink"))
    assert err and "colour" in err.lower()


def test_validate_bad_system(tmp_path: Path) -> None:
    err = validate(_good(tmp_path, system="burda"))
    assert err and "pattern system" in err.lower()


def test_validate_bad_birthday(tmp_path: Path) -> None:
    err = validate(_good(tmp_path, birthday="17/05/1990"))
    assert err and "yyyy-mm-dd" in err.lower()


def test_validate_empty_birthday_is_ok(tmp_path: Path) -> None:
    assert validate(_good(tmp_path, birthday="")) is None


# ---------------------------------------------------------------------------
# build_cmd
# ---------------------------------------------------------------------------


def test_build_cmd_minimal(tmp_path: Path) -> None:
    cmd = build_cmd(_good(
        tmp_path, color="none", birthday="", person="Yaiza",
        csv="on", obj="", smis="",
    ))
    assert cmd[0] == PIPELINE_PY
    assert cmd[1] == str(RUN_SCAN)
    assert cmd[2] == str(tmp_path)
    assert "--out-prefix" in cmd
    assert "--pattern-system" in cmd
    assert "--export-csv" in cmd
    assert "--no-export-obj" in cmd
    assert "--no-export-smis" in cmd
    assert "--waist-color" not in cmd
    assert "--person-birth-date" not in cmd
    assert "--person-given-name" in cmd
    assert cmd[cmd.index("--person-given-name") + 1] == "Yaiza"
    assert "--person-family-name" not in cmd  # single-token name


def test_build_cmd_full(tmp_path: Path) -> None:
    cmd = build_cmd(_good(
        tmp_path, color="cyan", birthday="1990-05-17",
        person="Yaiza Gomez Perez", system="all",
    ))
    assert ["--waist-color", "cyan"] == [
        cmd[cmd.index("--waist-color")],
        cmd[cmd.index("--waist-color") + 1],
    ]
    assert ["--person-birth-date", "1990-05-17"] == [
        cmd[cmd.index("--person-birth-date")],
        cmd[cmd.index("--person-birth-date") + 1],
    ]
    assert cmd[cmd.index("--person-given-name") + 1] == "Yaiza"
    assert cmd[cmd.index("--person-family-name") + 1] == "Gomez Perez"
    assert cmd[cmd.index("--pattern-system") + 1] == "all"


# ---------------------------------------------------------------------------
# Runner state machine
# ---------------------------------------------------------------------------


def _drain(runner: Runner, *, timeout: float = 5.0) -> list[dict]:
    """Collect messages from runner.q until {'done': True} or timeout."""
    deadline = time.monotonic() + timeout
    msgs: list[dict] = []
    while time.monotonic() < deadline:
        try:
            msg = runner.q.get(timeout=0.2)
        except Exception:  # noqa: BLE001 — queue.Empty
            continue
        msgs.append(msg)
        if msg.get("done"):
            return msgs
    raise TimeoutError("runner did not finish in time")


def test_runner_runs_to_completion(tmp_path: Path) -> None:
    runner = Runner(cwd=tmp_path)
    runner.start(["/bin/sh", "-c", "echo hello; echo world"])
    msgs = _drain(runner)
    # First message is the command echo.
    assert msgs[0]["line"].startswith("$ ")
    body = "".join(m["line"] for m in msgs if "line" in m)
    assert "hello" in body and "world" in body
    assert msgs[-1] == {"done": True, "rc": 0}
    assert not runner.is_running()


def test_runner_rejects_double_start(tmp_path: Path) -> None:
    runner = Runner(cwd=tmp_path)
    runner.start(["/bin/sh", "-c", "sleep 0.5"])
    with pytest.raises(RuntimeError, match="already running"):
        runner.start(["/bin/sh", "-c", "echo nope"])
    _drain(runner)  # let the first one finish so no zombie.


def test_runner_cancel_terminates(tmp_path: Path) -> None:
    runner = Runner(cwd=tmp_path)
    runner.start(["/bin/sh", "-c", "sleep 30"])
    assert runner.is_running()
    runner.cancel()
    msgs = _drain(runner, timeout=3.0)
    assert msgs[-1]["done"] is True
    assert msgs[-1]["rc"] != 0
    assert any("cancelled" in m.get("line", "") for m in msgs)


def test_runner_cancel_idle_is_noop(tmp_path: Path) -> None:
    runner = Runner(cwd=tmp_path)
    runner.cancel()  # nothing running; must not raise.
    assert not runner.is_running()

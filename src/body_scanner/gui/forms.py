"""Pure form helpers: slug, split name, validate, build subprocess args.

These functions only consume plain dicts (the route handler passes
``request.form.to_dict()``) so they're directly unit-testable without
spinning up Flask.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Mapping

from .config import (
    ENABLED_GENDERS,
    PIPELINE_PY,
    RUN_SCAN,
    VALID_GENDERS,
    VALID_PATTERN_SYSTEMS,
    WAIST_COLORS,
)


_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(name: str) -> str:
    """Lowercase, ASCII, underscore-separated stem. Empty → 'scan'."""
    s = (name or "").strip().lower()
    s = _SLUG_RE.sub("_", s).strip("_")
    return s or "scan"


def split_person_name(person: str) -> tuple[str, str]:
    """Split a free-text name on whitespace: first token → given name,
    remainder → family name."""
    parts = (person or "").strip().split()
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], " ".join(parts[1:])


def validate(form: Mapping[str, str]) -> str | None:
    """Return None when the form is acceptable, else a human-readable error.

    Mirrors run_scan.py's prerequisites: capture folder must exist on
    disk; person name + output prefix non-empty; at least one export
    artifact selected; waist colour & pattern system inside the
    allowed sets.
    """
    capture = (form.get("capture") or "").strip()
    person = (form.get("person") or "").strip()
    out_prefix = (form.get("out_prefix") or "").strip()

    if not capture:
        return "Pick a Stray capture folder."
    if not Path(capture).is_dir():
        return f"Capture folder does not exist: {capture}"
    if not person:
        return "Enter a person name."
    if not out_prefix:
        return "Output prefix is empty."
    if not (form.get("csv") or form.get("obj") or form.get("smis")):
        return "Pick at least one export artifact."

    color = (form.get("color") or "none").strip()
    if color not in WAIST_COLORS:
        return f"Unknown waist colour: {color!r}"

    system = (form.get("system") or "all").strip()
    if system not in VALID_PATTERN_SYSTEMS:
        return f"Unknown pattern system: {system!r}"

    gender = (form.get("gender") or "female").strip()
    if gender not in VALID_GENDERS:
        return f"Unknown gender: {gender!r}"
    if gender not in ENABLED_GENDERS:
        return (f"Gender {gender!r} is not currently supported "
                "(no SMPL-X model file present).")

    bday = (form.get("birthday") or "").strip()
    if bday and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", bday):
        return f"Birthday must be yyyy-mm-dd: {bday!r}"
    return None


def build_cmd(form: Mapping[str, str]) -> list[str]:
    """Translate the validated form into the run_scan.py argv list.

    Caller is expected to have run :func:`validate` first; this function
    trusts the input and emits flags in a stable order so tests can
    assert exact argv content.
    """
    capture = (form.get("capture") or "").strip()
    out_prefix = (form.get("out_prefix") or "").strip()
    given, family = split_person_name(form.get("person") or "")
    csv_flag = "--export-csv" if form.get("csv") else "--no-export-csv"
    obj_flag = "--export-obj" if form.get("obj") else "--no-export-obj"
    smis_flag = "--export-smis" if form.get("smis") else "--no-export-smis"

    gender = (form.get("gender") or "female").strip()
    cmd: list[str] = [
        PIPELINE_PY, str(RUN_SCAN), capture,
        "--out-prefix", out_prefix,
        "--pattern-system", form.get("system") or "all",
        "--gender", gender,
        csv_flag, obj_flag, smis_flag,
    ]
    color = (form.get("color") or "none").strip()
    if color != "none":
        cmd.extend(["--waist-color", color])
    bday = (form.get("birthday") or "").strip()
    if bday:
        cmd.extend(["--person-birth-date", bday])
    if given:
        cmd.extend(["--person-given-name", given])
    if family:
        cmd.extend(["--person-family-name", family])
    return cmd

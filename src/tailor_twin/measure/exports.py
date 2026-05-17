"""Artifact writers for the measurement pipeline.

Three outputs from a single fit + extract run:
  - .smis      (SeamlyMe / Seamly2D) — formula-derived codes are
                written as Seamly2D-evaluable expressions in the
                ``value`` attribute (e.g. ``value="(neck_circ - neck_arc_f)"``),
                so editing a primary in SeamlyMe re-derives all
                dependents the next time the .smis is loaded.
  - .csv       (code, seamly_name, value_cm)        — Seamly catalog
  - .obj       (fitted SMPL-X body mesh — CLO3D-importable)
"""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

import numpy as np

from .seamly_catalog import CODE_TO_NAME, FORMULAS


# Seamly code pattern: capital letter + two digits. Used to translate
# the FORMULAS dict expressions (which reference codes like ``G02``)
# into Seamly2D-evaluable formulas referencing names like ``neck_circ``.
_CODE_REF = re.compile(r"\b([A-Z]\d{2})\b")


def _formula_to_seamly(expr: str) -> str:
    """Replace every ``<code>`` in an arithmetic expression with the
    matching Seamly measurement name. Codes without a known name (e.g.
    the literal ``0`` in the ``A23`` placeholder) are left alone, so a
    formula like ``"A02 - 0"`` survives the substitution untouched."""

    def repl(m: re.Match[str]) -> str:
        return CODE_TO_NAME.get(m.group(1), m.group(1))

    return _CODE_REF.sub(repl, expr)


def _build_formula_strings() -> dict[str, str]:
    """Map Seamly *name* → formula expression in Seamly *names*.

    Keyed by name (not code) because the SMIS XML uses names. Only
    formula codes that have a registered Seamly name are emitted —
    others are dropped (they'd be unreachable from the SMIS anyway)."""
    out: dict[str, str] = {}
    for code, formula in FORMULAS.items():
        name = CODE_TO_NAME.get(code)
        if name is None:
            continue
        out[name] = f"({_formula_to_seamly(formula.expr)})"
    return out


# ---------------------------------------------------------------------------
# Personal info (optional SMIS <personal> block)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PersonalInfo:
    """Sewer identity for the SMIS <personal> block.

    Empty / None fields fall through to SeamlyMe defaults (empty
    element or '1800-01-01' for birth_date)."""

    given_name: str = ""
    family_name: str = ""
    birth_date: str = ""   # ISO yyyy-mm-dd; falls back to 1800-01-01
    gender: str = ""       # "female" / "male" / "unknown"
    email: str = ""


# ---------------------------------------------------------------------------
# CSV
# ---------------------------------------------------------------------------


def write_csv(
    catalog_values: dict[str, float],
    out_path: Path,
    include_judgment_blank: bool = False,
) -> None:
    """Emit `code, seamly_name, value_cm` rows for the catalog values.

    If include_judgment_blank is True, also write rows for codes we know
    about (CODE_TO_NAME) but couldn't extract — value_cm column empty.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["code", "seamly_name", "value_cm"])

        # Order: catalog code lexicographic.
        codes = sorted(set(catalog_values) | (set(CODE_TO_NAME)
                                              if include_judgment_blank else set()))
        for code in codes:
            name = CODE_TO_NAME.get(code, "")
            v = catalog_values.get(code)
            v_str = f"{float(v):.4f}" if v is not None else ""
            w.writerow([code, name, v_str])


# ---------------------------------------------------------------------------
# OBJ (fitted SMPL-X body mesh)
# ---------------------------------------------------------------------------


def write_obj(verts: np.ndarray, faces: np.ndarray, out_path: Path) -> None:
    """Wavefront OBJ with per-vertex normals + smoothing group enabled.

    `vn` + `s 1` make Blender / CLO3D shade the mesh smoothly on import
    (no manual Shade-Smooth step). SMPL-X has 10475 verts and 20908
    triangles, all manifold."""
    fn = np.cross(
        verts[faces[:, 1]] - verts[faces[:, 0]],
        verts[faces[:, 2]] - verts[faces[:, 0]],
    )
    fn /= np.linalg.norm(fn, axis=1, keepdims=True).clip(min=1e-12)
    vn = np.zeros_like(verts)
    for i in range(3):
        np.add.at(vn, faces[:, i], fn)
    vn /= np.linalg.norm(vn, axis=1, keepdims=True).clip(min=1e-12)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w") as f:
        f.write("# tailor-twin fitted SMPL-X mesh\n")
        for v in verts:
            f.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
        for n in vn:
            f.write(f"vn {n[0]:.6f} {n[1]:.6f} {n[2]:.6f}\n")
        f.write("s 1\n")
        for tri in faces:
            a, b, c = tri[0]+1, tri[1]+1, tri[2]+1
            f.write(f"f {a}//{a} {b}//{b} {c}//{c}\n")


# ---------------------------------------------------------------------------
# SMIS (SeamlyMe / Seamly2D XML)
# ---------------------------------------------------------------------------


_PM_SYSTEM_DEFAULT = "998"
_PM_SYSTEMS: dict[str, str] = {
    # SeamlyMe pattern-making system codes. 998 = "Individual / custom".
    # Aldrich + dpm both default to 998 in our pipeline; future codes can
    # be wired here without touching call sites.
    "individual": "998",
    "aldrich": "998",
    "dpm": "998",
    "seamly": "998",
}


def _personal_block(p: PersonalInfo | None) -> str:
    family = xml_escape(p.family_name) if p and p.family_name else ""
    given = xml_escape(p.given_name) if p and p.given_name else ""
    birth = (p.birth_date if p and p.birth_date else "1800-01-01")
    gender = (p.gender if p and p.gender else "unknown")
    email = xml_escape(p.email) if p and p.email else ""
    family_el = f"<family-name>{family}</family-name>" if family else "<family-name/>"
    given_el = f"<given-name>{given}</given-name>" if given else "<given-name/>"
    email_el = f"<email>{email}</email>" if email else "<email/>"
    return (
        "    <personal>\n"
        f"        {family_el}\n"
        f"        {given_el}\n"
        f"        <birth-date>{birth}</birth-date>\n"
        f"        <gender>{xml_escape(gender)}</gender>\n"
        f"        {email_el}\n"
        "    </personal>\n"
    )


def render_smis(
    seamly_values: dict[str, float],
    template_order: list[str],
    personal: PersonalInfo | None = None,
    pm_system: str = _PM_SYSTEM_DEFAULT,
    formulas: dict[str, str] | None = None,
) -> str:
    """Render an .smis XML string.

    ``seamly_values`` is keyed by SEAMLY NAME (e.g. 'bust_circ').
    ``formulas`` maps a name to a Seamly2D-evaluable expression (in
    Seamly names, not codes) — names appearing here are written with
    the formula in the ``value`` attribute so SeamlyMe re-derives
    them at load time instead of carrying our precomputed number.
    Names absent from ``formulas`` use the numeric value as before.
    """
    formulas = formulas or {}
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    head = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<smis>\n"
        f"    <!--Generated by tailor_twin.measure.exports on {now}-->\n"
        "    <version>0.3.4</version>\n"
        "    <read-only>false</read-only>\n"
        "    <notes/>\n"
        "    <unit>cm</unit>\n"
        f"    <pm_system>{xml_escape(str(pm_system))}</pm_system>\n"
        + _personal_block(personal)
        + "    <body-measurements>\n"
    )

    def _value_attr(name: str) -> str:
        if name in formulas:
            return xml_escape(formulas[name])
        val = seamly_values[name]
        if isinstance(val, float) and val.is_integer():
            val = int(val)
        return str(val)

    # Only emit measurements we actually extracted (numeric value) or
    # know how to derive (formula). Names listed in the template but
    # absent from both are skipped — Seamly2D users can re-add them
    # manually if needed.
    available = set(seamly_values) | set(formulas)

    rows: list[str] = []
    seen: set[str] = set()
    for name in template_order:
        if name not in available:
            continue
        rows.append(
            f'        <m name="{xml_escape(name)}" value="{_value_attr(name)}"/>'
        )
        seen.add(name)
    for name in sorted(available - seen):
        rows.append(
            f'        <m name="{xml_escape(name)}" value="{_value_attr(name)}"/>'
        )
    tail = "\n    </body-measurements>\n</smis>\n"
    return head + "\n".join(rows) + tail


def write_smis_from_catalog(
    catalog_values: dict[str, float],
    out_path: Path,
    template_path: Path | None = None,
    personal: PersonalInfo | None = None,
    pm_system: str = _PM_SYSTEM_DEFAULT,
) -> None:
    """Convert {code: value} -> {seamly_name: value} via CODE_TO_NAME, render
    XML, write to disk. Formula codes (entries in ``FORMULAS``) are
    written as Seamly2D expressions in the ``value`` attribute so
    SeamlyMe re-derives them when the .smis is loaded — primary
    edits propagate to dependents without re-running the pipeline.
    ``personal`` populates the SMIS <personal> block.
    """
    formula_strings = _build_formula_strings()
    formula_names = set(formula_strings)

    by_name: dict[str, float] = {}
    for code, val in catalog_values.items():
        name = CODE_TO_NAME.get(code)
        if not name:
            continue
        # Skip formula values — they'll be emitted as Seamly2D
        # expressions, not precomputed numbers.
        if name in formula_names:
            continue
        by_name[name] = float(val)

    template_order: list[str] = []
    if template_path and Path(template_path).is_file():
        template_order = re.findall(
            r'<m\s+name="([^"]+)"', Path(template_path).read_text()
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        render_smis(by_name, template_order,
                    personal=personal, pm_system=pm_system,
                    formulas=formula_strings))



"""Artifact writers for the measurement pipeline.

Four outputs from a single fit + extract run:
  - .smis      (SeamlyMe / Seamly2D)
  - .csv       (code, seamly_name, value_cm)        — Seamly catalog
  - .csv       (name, value_cm) named-CSV variant   — Aldrich / dpm
  - .obj       (fitted SMPL-X body mesh — CLO3D-importable)

The SMIS writer mirrors scripts/export_seamlyme.py's render_smis but is
importable so the measure CLI can produce the .smis directly.
"""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

import numpy as np

from .seamly_catalog import CODE_TO_NAME


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
        f.write("# body-scanner fitted SMPL-X mesh\n")
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
) -> str:
    """Same XML shape as scripts/export_seamlyme.py::render_smis.
    seamly_values is keyed by SEAMLY NAME (e.g. 'bust_circ'), not code."""
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    head = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<smis>\n"
        f"    <!--Generated by body_scanner.measure.exports on {now}-->\n"
        "    <version>0.3.4</version>\n"
        "    <read-only>false</read-only>\n"
        "    <notes/>\n"
        "    <unit>cm</unit>\n"
        f"    <pm_system>{xml_escape(str(pm_system))}</pm_system>\n"
        + _personal_block(personal)
        + "    <body-measurements>\n"
    )
    rows: list[str] = []
    seen: set[str] = set()
    for name in template_order:
        val = seamly_values.get(name, 0)
        if isinstance(val, float) and val.is_integer():
            val = int(val)
        rows.append(f'        <m name="{xml_escape(name)}" value="{val}"/>')
        seen.add(name)
    for name in sorted(set(seamly_values) - seen):
        val = seamly_values[name]
        if isinstance(val, float) and val.is_integer():
            val = int(val)
        rows.append(f'        <m name="{xml_escape(name)}" value="{val}"/>')
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
    XML, write to disk. ``personal`` populates the SMIS <personal> block."""
    by_name: dict[str, float] = {}
    for code, val in catalog_values.items():
        name = CODE_TO_NAME.get(code)
        if name:
            by_name[name] = float(val)

    template_order: list[str] = []
    if template_path and Path(template_path).is_file():
        template_order = re.findall(
            r'<m\s+name="([^"]+)"', Path(template_path).read_text()
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        render_smis(by_name, template_order,
                    personal=personal, pm_system=pm_system))


# ---------------------------------------------------------------------------
# Named CSV (Aldrich / dpm — merged.yaml output)
# ---------------------------------------------------------------------------


# Name-prefix → pattern-making system. Used to filter merged.yaml output
# when the GUI / CLI asks for a single-system CSV export.
SYSTEM_PREFIXES: dict[str, tuple[str, ...]] = {
    "all": (),
    "aldrich": ("aldrich_",),
    "dpm": ("dpm_", "bustpoint_"),
}


def filter_by_system(
    values: dict[str, float], system: str,
) -> dict[str, float]:
    """Keep only entries whose name starts with one of SYSTEM_PREFIXES[system].

    ``system='all'`` returns the input dict unchanged. Unknown systems
    raise KeyError so typos surface early."""
    prefixes = SYSTEM_PREFIXES[system]
    if not prefixes:
        return dict(values)
    return {k: v for k, v in values.items() if k.startswith(prefixes)}


def write_named_csv(
    values: dict[str, float], out_path: Path,
) -> None:
    """Emit ``name, value_cm`` rows ordered alphabetically. ``values`` is
    keyed by the merged.yaml entry name (e.g. 'aldrich_bust')."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["name", "value_cm"])
        for k in sorted(values):
            w.writerow([k, f"{float(values[k]):.4f}"])

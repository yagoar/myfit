"""Cross-figure robustness gate.

For every Seamly code present in both the yaiza and carmen baseline
CSVs, assert the height-normalised drift between the two figures
stays within a per-code budget. Stops a future landmark / primitive
change from silently regressing the figure-robustness work tracked in
``data/review/figure_robustness_checklist.md``.

Drift definition:

    drift = (carmen_value / yaiza_value) / height_ratio - 1

A drift of 0 means the carmen measurement is exactly what you'd
predict from scaling yaiza's value by the height ratio. Real
anatomical variation (waist-to-crotch span, shoulder slope) is
allowed via an explicit per-code allowlist; everything else has to
sit within ``DEFAULT_BUDGET``.

Regenerate the baselines via::

    python -m tailor_twin.measure.cli data/results/<name>_smplx_fit.npz \\
        --both --num-betas 300 \\
        --save-csv data/results/<name>_measurements.baseline.csv
"""
from __future__ import annotations

import csv
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
YAIZA_CSV = REPO_ROOT / "data" / "results" / "yaiza_measurements.baseline.csv"
CARMEN_CSV = REPO_ROOT / "data" / "results" / "carmen_measurements.baseline.csv"

# Default tolerance — any code without a specific entry below.
DEFAULT_BUDGET = 0.10  # ±10 %

# Per-code budgets for measurements that drift due to real anatomical
# variation between figures, not measurement-logic bugs. Tightening
# these requires a fit / pose fix, not a measurement change. Numbers
# come from the audit work in figure_robustness_checklist.md.
RELAXED_BUDGETS: dict[str, float] = {
    # acromion / shoulder slope — vertex-ID stability across betas
    # (see checklist §6, deferred until tape calibration).
    "H39": 0.30,  # shoulder_slope_neck_back_height
    "H37": 0.15,  # shoulder_slope_neck_side_length
    "L16": 0.20,  # arm_shoulder_tip_to_armfold_line
    # ankle bone height: anatomical foot-height variation (the
    # verified vid is shape-invariant, but how high the malleolus
    # sits above the floor is per-body).
    "A11": 0.40,  # height_ankle (ankle_bone_lateral_left vid Y)
    "A10": 0.25,  # height_ankle_high (depends on ankle bone Y)
    "M09": 0.15,  # leg_ankle_circ (ankle bone girth)
    # Underbust crease drop_fraction is a constant 0.5 — not yet
    # bust-depth aware (checklist §4). Keep tolerance at ±10 % so a
    # future calibration win is visible, but accept noise for now.
}

# Codes intentionally skipped from drift checks. Reserved for cases
# where the measurement is figure-defined (skirt length, custom
# allowances) — currently none in the Seamly catalog.
SKIP_CODES: frozenset[str] = frozenset()

# Below this absolute value (cm) the relative-drift number is too
# noisy to be meaningful. A code reading 0.5 cm with a 0.1 cm absolute
# jitter would report 20 % drift even though both figures match.
MIN_ABS_CM = 1.0


def _load(path: Path) -> dict[str, tuple[str, float]]:
    if not path.is_file():
        pytest.skip(f"baseline missing: {path}")
    out: dict[str, tuple[str, float]] = {}
    with path.open() as fh:
        for row in csv.DictReader(fh):
            out[row["code"]] = (row["seamly_name"], float(row["value_cm"]))
    return out


def _budget(code: str) -> float:
    return RELAXED_BUDGETS.get(code, DEFAULT_BUDGET)


def test_carmen_vs_yaiza_drift_within_budget() -> None:
    yaiza = _load(YAIZA_CSV)
    carmen = _load(CARMEN_CSV)
    if "A01" not in yaiza or "A01" not in carmen:
        pytest.skip("A01 height missing from one of the baselines")
    height_ratio = carmen["A01"][1] / yaiza["A01"][1]

    failures: list[str] = []
    for code in sorted(set(yaiza) & set(carmen)):
        if code in SKIP_CODES:
            continue
        name, yv = yaiza[code]
        _, cv = carmen[code]
        if abs(yv) < MIN_ABS_CM or abs(cv) < MIN_ABS_CM:
            continue
        drift = (cv / yv) / height_ratio - 1.0
        budget = _budget(code)
        if abs(drift) > budget:
            failures.append(
                f"  {code} {name}: drift {drift:+.1%} exceeds budget "
                f"±{budget:.0%}  (yaiza={yv:.2f}cm, carmen={cv:.2f}cm)"
            )
    if failures:
        pytest.fail(
            f"{len(failures)} code(s) drift beyond budget — investigate "
            "or update RELAXED_BUDGETS / SKIP_CODES with a justification:\n"
            + "\n".join(failures)
        )

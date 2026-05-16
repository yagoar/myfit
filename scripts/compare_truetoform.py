#!/usr/bin/env python3
"""Compare our measurement extractor output against truetoform.fit's CSV.

truetoform.fit (the scanning service) returns its own measurement list with
human-readable names. Our extractor emits Seamly catalog codes. This script
joins them by hand-mapped names and prints a diff table.

Usage:
    scripts/compare_truetoform.py
"""
from __future__ import annotations

import csv
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TRUE = REPO / "data" / "body_models" / "yaiza_metrics.csv"
OURS = REPO / "data" / "results" / "yaiza_measurements.csv"


# truetoform name -> our Seamly code
MAPPING: dict[str, str] = {
    # Circumferences
    "Neck":              "G01",   # neck_mid_circ
    "Neck Base":         "G02",   # neck_circ
    # truetoform's "Overbust" = highbust_circ (over bust, under armpits)
    # truetoform's "Upper Chest" is the planar slice just under armpits;
    # no Seamly code for it (closest is G03 but the conventions differ).
    "Overbust":          "G03",   # highbust_circ
    "Bust":              "G04",   # bust_circ
    "Under Bust":        "G05",   # lowbust_circ
    "Waist":             "G07",   # waist_circ
    "Hip":               "G09",   # hip_circ
    "Right Bicep":       "L11",
    "Right Elbow":       "L13",
    "Left Wrist":        "L15",
    "Left Thigh":        "M03",
    "Left Knee":         "M05",
    "Left Calf":         "M07",   # we use ankle_bone vid as placeholder
    "Left Ankle":        "M09",

    # Lengths
    "Left Shoulder":     "I01",   # shoulder_neck -> acromion geodesic
    "Left Arm":          "L05",   # acromion -> wrist
    "Shoulder Width Horizontal": "B01",  # acromion-to-acromion chord
    "Across Chest":      "I03",   # armscye-to-armscye front
    "Across Back":       "I08",   # armscye-to-armscye back
    "Apex to Apex":      "J01",   # bustpoint_to_bustpoint
    "Left High Point Shoulder to Bust":  "H14",  # neck_side_to_bust_f
    "Left High Point Shoulder to Waist": "H05",  # neck_side_to_waist_f
    "Hollow to Floor":   "A16",   # height_neck_front
    "Nape to Upper Chest Center Back": "H21",  # neck_back_to_highbust_b
    "Nape to Waist Center Back": "H19",  # neck_back_to_waist_b
    "Total Crotch Length": "N01",
    "Front Crotch Length": "N03",
    "Back Crotch Length":  "N02",
    "Left Side Pant Inseam": "M01",  # crotch_to_floor (approx)
    "Left Outseam Waist To Floor": "M02",  # waist_side_to_floor
}


def main() -> None:
    truth: dict[str, float] = {}
    with TRUE.open() as f:
        for row in csv.DictReader(f):
            truth[row["Name"]] = float(row["Value (cm)"])

    ours: dict[str, float] = {}
    with OURS.open() as f:
        for row in csv.DictReader(f):
            if row["value_cm"]:
                ours[row["code"]] = float(row["value_cm"])

    rows: list[tuple[str, str, float, float, float, float]] = []
    for name, code in MAPPING.items():
        t = truth.get(name)
        o = ours.get(code)
        if t is None or o is None:
            continue
        diff = o - t
        pct = 100.0 * diff / t if t else 0.0
        rows.append((name, code, t, o, diff, pct))

    # Print sorted by |diff %| desc
    rows.sort(key=lambda r: -abs(r[5]))
    print(f"{'truetoform name':<38} {'code':<5} "
          f"{'truth':>7} {'ours':>7} {'diff':>7} {'diff%':>7}")
    print("-" * 78)
    for name, code, t, o, d, p in rows:
        print(f"{name:<38} {code:<5} {t:>7.2f} {o:>7.2f} {d:>+7.2f} {p:>+6.1f}%")

    diffs = [abs(r[4]) for r in rows]
    pcts = [abs(r[5]) for r in rows]
    print()
    print(f"n={len(rows)}  mean |diff|={sum(diffs)/len(diffs):.2f}cm  "
          f"max |diff|={max(diffs):.2f}cm  "
          f"mean |diff%|={sum(pcts)/len(pcts):.1f}%")


if __name__ == "__main__":
    main()

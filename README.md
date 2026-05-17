# TailorTwin

Personal 3D body measurement tool for sewing pattern drafting.

Capture yourself with an iPhone Pro LiDAR sensor, fit a parametric body
model (SMPL-X+D) to the scan, extract the 160+ measurements that the
**Aldrich** (5th ed.) and **dresspatternmaking.com** systems need to
draft bodice / sleeve / skirt / pants blocks, and view everything in a
browser-based 3D viewer with measurement overlays.

This is a single-user, local-only project. No cloud, no auth, no
shared backend.

---

## Quickstart

```bash
git clone <repo> tailor-twin && cd tailor-twin
python -m venv .venv && source .venv/bin/activate
pip install -e .
# Drop SMPL-X model file into data/body_models/smplx/SMPLX_FEMALE.npz
# (get it from https://smpl-x.is.tue.mpg.de/)
tailor-twin gui                    # opens http://127.0.0.1:8060/
```

Fill in the form, pick a Stray Scanner capture folder, hit **Run scan**.
First-time runs take ~3-6 min on Apple Silicon.

## CLI

After `pip install -e .` the `tailor-twin` console script is on PATH:

| Command | Purpose |
|---|---|
| `tailor-twin gui` | Web GUI (Flask + Three.js viewer) |
| `tailor-twin scan CAPTURE --out-prefix data/results/NAME` | End-to-end pipeline |
| `tailor-twin preflight CAPTURE` | Pre-scan capture sanity check |
| `tailor-twin bent-arm FIT_NPZ` | Re-pose elbow + dump L01/L02/L04 |
| `tailor-twin <cmd> --help` | Full flag list per command |

Direct module invocation also works: `python -m tailor_twin.scan …`,
`python -m tailor_twin.measure.cli …`.

## Pipeline

```
Stray capture       →  preprocess  →  TSDF fuse  →  cleanup
   (rgb + depth        (segment +     (Open3D       (largest
    + confidence        depth filter)  ScalableTSDF)  component,
    + odometry)                                       smooth,
                                                      decimate)
   ↓
SMPL-X+D fit       →  measure       →  bent-arm     →  exports
  (300 betas +        (167 Seamly        re-pose       (CSV, OBJ,
   per-vertex          catalog codes +   for L01/      SMIS,
   displacement)        Aldrich/dpm)     L02/L04)      JSON)
```

All artefacts written next to the user-chosen `--out-prefix`:

```
data/results/yaiza_20260517_scan.obj          # cleaned TSDF mesh
data/results/yaiza_20260517_smplx_fit.npz     # fit parameters
data/results/yaiza_20260517_fit_body.obj      # fitted body mesh
data/results/yaiza_20260517_measurements.csv  # Seamly catalog
data/results/yaiza_20260517_aldrich.csv       # filtered named CSV
data/results/yaiza_20260517_seamly_catalog.json
data/results/yaiza_20260517.smis              # SeamlyMe XML
data/results/yaiza_20260517_bent_arm.{json,npz}
data/results/yaiza_20260517_waist_y.json      # if elastic detected
```

## Package layout

```
src/tailor_twin/
  cli.py            # Typer console script entry
  scan.py           # full pipeline runner (was scripts/run_scan.py)
  preflight.py      # capture pre-flight inspector
  io/               # Stray Scanner frame loader
  preprocess/       # depth filter, segmentation, waist-string detect
  reconstruct/      # TSDF fuse + mesh cleanup
  fit/              # SMPL-X+D mesh-to-mesh fitter
  measure/          # landmarks, recipes, Seamly catalog, exports
  gui/              # Flask app + Three.js viewer
scripts/            # dev utilities (regenerate docs, direct exports)
tests/              # unit + snapshot regression
docs/               # measurement catalog, recipes glossary
references/         # source PDFs/notes for Aldrich + dpm
```

## Docs

- [`SPEC.md`](SPEC.md) — project spec (pipeline, accuracy targets, schema)
- [`GUARDRAILS.md`](GUARDRAILS.md) — AI-generation rules for this repo
- [`docs/recipes.md`](docs/recipes.md) — measurement-recipe glossary
- [`docs/catalog_coverage.md`](docs/catalog_coverage.md) — auto-generated table of every Seamly code + status
- [`src/tailor_twin/measure/README.md`](src/tailor_twin/measure/README.md) — measure subpackage overview

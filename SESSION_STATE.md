# Session State (handoff)

Last updated: 2026-05-15, end of working session.

This document captures the full state of the body-scanner project so a
future session (a different Claude, or future-you) can pick up without
re-reading every commit. **`SPEC.md` is still the authoritative spec;
this file is a working journal that complements it.**

## What this project is

Personal LiDAR-based body scanner for sewing-pattern drafting. iPhone Pro
captures via Stray Scanner → AirDrop to Mac → Python pipeline (segment,
TSDF fuse, SMPL-X+D fit, extract ~45 measurements covering both Aldrich
and dresspatternmaking.com systems) → SQLite + OBJ + worksheet, plus an
optional Seamly2D/SeamlyMe `.smis` export.

Single-user (Yaiza), local-only, no cloud, female-target. Python 3.12.13
pinned (Open3D 0.19 wheel cap).

## Where things stand by phase (SPEC §10)

| Phase | Status | Notes |
|---|---|---|
| 0 — repo setup, deps, SMPL-X load | **DONE** | `scripts/verify_phase0.py` passes asserts + Open3D viewer; SMPLX_FEMALE.npz loaded. |
| 1 — Stray Scanner loader | **skeleton** | `src/body_scanner/io/stray_loader.py` written against the public format spec at github.com/strayrobots/scanner/docs/format.md. **Pending real-capture validation** — user's iPhone is unavailable until husband returns from a trip (was due Sunday after the session was conducted). |
| 2 — Segmentation + TSDF fusion | not started | |
| 3 — Landmarks + initial pose | not started | |
| 4 — SMPL-X+D fitting | not started | |
| 5 — Constructional lines | **scaffolded** | Landmark picker script + vertex-ID inventory skeleton in place. Actual Blender verification + screenshot capture pending. See `scripts/pick_smplx_landmarks.py` and `references/smplx_vertex_landmarks.md`. |
| 6 — Measurement extraction | **partial** | `merged.yaml` has all 72 definitions with sources, frames, and Seamly cross-walk. Code in `measure/extractor.py` not yet written. |
| 7 — Calibration | not started | User-bottlenecked (tape measurements). |
| 8 — SQLite + worksheet | not started | FREE territory; can be scaffolded any time. |
| 9 — SVG block generation | optional | Source PDFs / videos in place. |
| 10 — Custom iOS capture app | optional, deferred | |

## Commits in chronological order (most recent first)

```
640f963  feat(seamly): cross-walk merged.yaml to SeamlyMe + export script
43c85c8  feat(review): single-card-per-page navigation in review.html
054f715  feat: review pass on remaining dpm transcripts + review.html generator
7080ee6  refactor(ingest): rename frames to timestamp form frame_HHhMMmSSs.jpg
ccd2352  docs(measure): add verified frame citations to 14 high-value dpm entries
c722d4f  feat(measure): add dpm bodice/sleeve/pants definitions + revisions
5ce7c98  feat(measure): transcribe Aldrich book p.13 standard body measurements
cf8c62b  feat: Stray loader skeleton + Aldrich p.178-179 measurement definitions
531dbc1  docs(spec): log canonical-measurement-pose open questions
28b8945  feat(phase-0): repo scaffolding, deps, SMPL-X load verification
dcbf94d  feat(ingest): add dpm video transcripts and frames
d98c181  chore: bootstrap repo scaffolding
```

## File map

### Authoritative

| File | What |
|---|---|
| `SPEC.md` | Project spec. Sections 5 (sources), 9 (measurement schema), 13 (risks), 16 (open questions). |
| `GUARDRAILS.md` | AI-generation rules (FREE / RISKY / FORBIDDEN). |
| `pyproject.toml` | Python 3.12 pin, deps from SPEC §15, hatchling backend. |
| `.python-version` | `3.12.13` for pyenv. |

### Reference materials (`references/`)

| File / Folder | What |
|---|---|
| `references/smplx_vertex_landmarks.md` | Phase 5 inventory of 48 anatomical vertex landmarks (45 required + 3 audit-judgment optional) the body-scanner pipeline needs. Each row has columns for `proposed_vertex_id` (from the Open3D picker) and `verified_vertex_id` (from the Blender check, with a screenshot under `references/smplx_landmark_screenshots/`). Currently empty — all rows pending. |
| `references/aldrich_full.pdf` | Aldrich 5th edition full book (LFS-tracked). |
| `references/aldrich_p178_179_notes.md` | Detailed transcription + diagram description of book p.178-179. |
| `references/dpm_bodice.pdf` | dresspatternmaking.com 2025 bodice block instructions (LFS). |
| `references/dpm_pants.pdf` | dresspatternmaking.com 2025 pants block instructions (LFS). |
| `references/dpm_videos/<topic>/transcript.{txt,srt}` | Whisper transcripts of the 9 ingested dpm videos. Audio + source videos are gitignored. |
| `references/dpm_videos/<topic>/frame_HHhMMmSSs.jpg` | Periodic frame captures (1924 total, LFS). Filename = video timestamp. |
| `references/seamly/` | **NEW this session.** Seamly2D measurement reference extracted from the Seamly2D `develop` branch (commit `8b6bc512a9`). Schemas, 107 SVG diagrams, sample `.smis` templates including `aldrich_women_template.smis`, full PDF guide, and a `README.md` with a 262-entry measurement catalog grouped A-Q. |

### Source code (`src/`)

| File | Status | What |
|---|---|---|
| `src/body_scanner/__init__.py` + subpackage `__init__.py` | scaffolded | Empty packages with one-line docstrings. |
| `src/body_scanner/io/stray_loader.py` | implemented (skeleton) | Yields `Frame(index, timestamp_s, rgb, depth_mm, confidence, intrinsics, pose_cam_to_world)`. Validates capture layout against Stray's documented format. **Untested against a real capture.** |
| `src/body_scanner/measure/definitions/merged.yaml` | populated | 72 measurement entries with `sources`, `notes`, `seamly_name`, `superseded_by` where applicable. 60 have a Seamly cross-walk; 12 are intentionally null. |
| `src/body_scanner/measure/definitions/aldrich_size_chart_p13.yaml` | populated | Aldrich's standard body-measurement chart from book p.13 (5th edition). 22 body rows + 4 garment rows + short/tall height adjustments. |
| Other subpackages (`preprocess`, `reconstruct`, `fit`, `construct`, `measure/extractor.py`, `blocks`, `viz`, `storage`) | empty | Created as scaffolding; no code yet. |

### Scripts (`scripts/`)

| File | What |
|---|---|
| `scripts/ingest_video.sh` | Bash. Ingests a video (URL via yt-dlp or local file) → ffmpeg audio + whisper.cpp transcription + ffmpeg frame extraction at a configurable interval → output under `references/<subpath>/`. Frames are renamed to `frame_HHhMMmSSs.jpg` form post-extraction. |
| `scripts/verify_phase0.py` | Loads SMPL-X FEMALE, asserts faces.shape == (20908, 3) and vertices.shape == (1, 10475, 3), opens an Open3D viewer with the T-pose mesh. `--no-viz` for headless. |
| `scripts/generate_review_html.py` | Reads `merged.yaml` and emits `review.html` (gitignored) at repo root: one card per measurement with inline frame thumbnails, per-entry localStorage notes, JSON + markdown export, name filter, prev/next pager with arrow-key navigation. |
| `scripts/export_seamlyme.py` | Reads a `{our_name: value_cm}` JSON + the `seamly_name` mapping from `merged.yaml` → emits a SeamlyMe `.smis` XML file matching the slot order of `~/seamly2d/templates/all_measurements_template.smis`. Conflict resolution prefers `dpm_*` over `aldrich_*`. Smoke-tested. **Slated for rewrite — see Parked design decisions below.** |
| `scripts/pick_smplx_landmarks.py` | Phase 5 helper. Loads `SMPLX_FEMALE.npz` T-pose, renders mesh + 20 orientation joint spheres (torso=blue, left=red, right=green), opens Open3D `VisualizerWithEditing` for Shift+click vertex picking. Prints picks (`vertex_id` + 3D coord) after window close; `--output picks.json` to save. Per GUARDRAILS §3, picks are proposed-only; final verification happens in Blender. Smoke-tested for load + geometry build. |

## Source material coverage

### Aldrich

| What | Source | Captured as |
|---|---|---|
| p.178 personal-measurement table (20 items + 2a Low waist) | `aldrich_full.pdf` book p.178 | `merged.yaml` aldrich_* entries 1-20 + 2a |
| p.179 "Taking measurements" instructions 1-20 + diagram | `aldrich_full.pdf` book p.179 | Same entries + `aldrich_p178_179_notes.md` |
| p.13 size chart | `aldrich_full.pdf` book p.13 | `aldrich_size_chart_p13.yaml` |

**Edition status (resolved):** PDF in repo is 5th edition; user owns 6th edition. Three 6th-edition photos added to `references/aldrich/` (IMG_9598=p.11 size chart, IMG_9599=p.214 measurement table, IMG_9600=p.215 diagram). **6th edition is now canonical.** Key differences:

| What | 5th edition | 6th edition |
|------|-------------|-------------|
| Size chart page | p.13 | p.11 |
| Measurement table | p.178 | p.214 |
| Diagram | p.179 | p.215 |
| Low waist offset | 6cm | **5cm** (updated in merged.yaml) |
| Size codes | 6–26, bust 76–122 (11 sizes) | 6–24, bust 80–122 (10 sizes) |
| Smallest size | bust 76 | dropped |
| Large-end values | original | retuned hips + top-arm |

Measurement instruction text is identical between editions except item 2a (5cm vs 6cm). Body values for corresponding bust sizes are the same except the largest 1–2 sizes.

### dpm

All 9 videos in scope have been transcribed via whisper.cpp + frame-sampled via ffmpeg. Frame intervals:
- `bodice_measurements`: 3 s
- everything else (`bodice_front`, `bodice_back`, `sleeve`, `pants_1..5`): 10 s

**Drafting-video revisions that supersede measurement-taking-video definitions** are tracked in `merged.yaml` via the `superseded_by:` field. Four current revisions:
1. `dpm_bodice_upper_bust` — body level is at the underarm, not 1 inch / 2.5 cm below it (bodice_front transcript:L40-49)
2. `dpm_bodice_upper_bust_front_arc` — same height revision applies (lives on same horizontal plane)
3. `dpm_bodice_upper_bust_back_arc` — same height revision applies
4. `dpm_bodice_side_length` — starts at the underarm, not at the upper-bust elastic

### New: `references/seamly/` (added this session by the user)

This is a major addition — extracted from Seamly2D's `develop` branch (commit `8b6bc512a9`). Contains:
- **`schema/`** — XSD schemas for `.smis` (individual) and `.smms` (multisize) measurement files.
- **`diagrams/`** — 107 SVG diagrams; one per measurement group (A-Q) at the page level (`Ap1.svg`, `Gp4.svg`, etc.). The README in that folder maps every measurement name to its diagram code.
- **`samples/`** — 4 sample `.smis` templates including `all_measurements_template.smis` (262 measurements with formulas) and **`aldrich_women_template.smis`** (an existing Aldrich-flavoured template).
- **`docs/`** — visual PDF guide.
- **`README.md`** — comprehensive catalog of all 262 Seamly measurements grouped A-Q with code, name, diagram, and "computed yes/no". This is the source of truth for what's a valid `seamly_name`.
- **`extraction_audit.md`** — Phase 6 planning artifact added this session. Classifies all 245 catalog entries as `mechanical` (154; well-defined scan extraction), `computed` (56; formula-derived, free), `judgment` (32; needs textual interpretation, fuzzy landmark, or pose-specific), or `standard` (3; size-chart Q-group dart widths). Result: **210 of 245 (86%) are "free" or mechanical** once landmarks are verified, motivating a single generic Seamly extractor pass rather than 245 hand-written `merged.yaml` entries.

**Seamly integration tasks (status):**
- ~~Validate every `seamly_name` in `merged.yaml` against the catalog in `references/seamly/README.md`.~~ **DONE:** all 60 mapped names valid against the 245-entry catalog. 11 expected duplicates (Aldrich+dpm → same Seamly name), 12 intentional nulls.
- Inspect `aldrich_women_template.smis` — it uses 7 custom `@M_1`..`@M_7` slots plus 7 named-string measurements ("Front Shoulder to Waist", "Waist to Knee", etc.) that Aldrich-specific drafting needs. Consider whether the body-scanner exporter should mirror that template's naming convention rather than the generic one. **TODO.**
- ~~Embed the matching diagram SVG in `review.html` per measurement card.~~ **DONE:** `generate_review_html.py` now parses `references/seamly/README.md` for the `seamly_name → diagram SVG` mapping (245 entries) and adds an `<img>` per card.
- ~~Add XSD validation to `scripts/export_seamlyme.py`.~~ **DONE:** validates output against `individual_measurements_v0.3.4.xsd` via `xmllint` after every write. `--no-validate` flag to skip.

## merged.yaml — current shape

74 entries, every one has a populated `sources` list:

- 21 Aldrich (items 1-20 + 2a Low waist) — `aldrich_*`
- 32 dpm bodice — `dpm_bodice_*` (numbering matches the dpm worksheet items 1-32)
- 5 dpm sleeve — `dpm_sleeve_*`
- 14 dpm pants — `dpm_pants_*` (12 core + 2 optional added from pants_3/4/5)
- 2 Seamly-compatibility geometric helpers (unprefixed) — `bustpoint_to_waist` (J04) and `bustpoint_to_shoulder_center` (J10). Not in Aldrich's p.178 list or any dpm video; added so the `aldrich_women_template.smis` slots and its custom @M_* formulas evaluate with real numbers. Sourced from the Seamly catalog. Both `source_classification: body` (scan-extractable as landmark-pair chords).

Schema (SPEC §9): each entry carries `name`, optional `aliases`, `seamly_name`, `type`, `parameters`, `sources` (list, primary first), `source_classification` (body / standard / derived), optional `notes`, optional `superseded_by`.

Pose references in `parameters` are symbolic: `pose.measurement_default`, `pose.bent_arm_aldrich`, `pose.bent_arm_sleeve_dpm`, `pose.knee_bent`. Exact joint angles are an open Phase 6 decision (SPEC §16).

Landmark references in `parameters` are also symbolic (`landmarks.c7`, `landmarks.bust_apex_midpoint`, `landmarks.upper_bust_level`, etc.). Per GUARDRAILS §3, no SMPL-X vertex IDs may be claimed until they're verified in Blender at Phase 5; the glossary at the top of `merged.yaml` documents the symbolic names.

14 entries have visually-verified frame citations alongside transcript citations; the rest are transcript-only (skipped because the slide-to-narration sync drifted in those segments — see commit `054f715` message for the list).

## review.html — what it is

Generated by `scripts/generate_review_html.py`. Open at `file:///<repo>/review.html`. One card per measurement with inline frame thumbnails. Notes per measurement save to browser localStorage. Two export buttons (JSON + markdown). Prev/next pager + arrow-key navigation + name filter + jump dropdown. The `seamly_name` shows as a green code chip when mapped, italic "null" when not. `review.html` itself is gitignored — regenerate with the script anytime `merged.yaml` changes.

## Open decisions parked in SPEC.md §16

- ~~Aldrich #4 Back Width vs dpm #31 Across Back: same height (15 cm below C7) or different?~~ **Resolved:** different. Aldrich = fixed 15 cm below C7; dpm = half C7-to-upper-bust (figure-dependent).
- Aldrich #12 High ankle exact offset (silent in book; provisional 5 cm).
- "Natural waist" geometric rule (Aldrich says "comfortable round the waist"; dpm says "smallest part of the torso").
- Canonical measurement pose exact joint angles ("modified T" vs pure T; Aldrich bent-arm angles; armhole intermediate pose if needed).
- Optimal SMPL-X vertex IDs for the symbolic landmarks (Phase 5 Blender work).
- dpm three-point armhole-depth waypoints precision.
- dpm bust depth B (CF) and C (FLF): along-surface or straight-line.
- Body-rise: expected offset between Aldrich seated and standing-scan derivation.
- ~~Which Aldrich edition is canonical~~ **Resolved:** 6th edition is canonical. PDF (5th ed) stays as digital reference; three 6th-ed photos in `references/aldrich/`. Low waist updated from 6cm to 5cm in merged.yaml.

## Parked design decisions

### Per-system Seamly export (decided 2026-05-15, not yet implemented)

The current `scripts/export_seamlyme.py` collapses Aldrich + dpm into a single `.smis`, resolving name collisions via a prefix-rank rule (`dpm_* > aldrich_*`, then alphabetical, see [export_seamlyme.py:89-93](scripts/export_seamlyme.py:89)). The rule is arbitrary — no rationale in code or commit `640f963`. Eleven slots collide (`bust_circ`, `waist_circ`, `hip_circ`, `shoulder_length`, `arm_upper_circ`, `arm_shoulder_tip_to_wrist_bent`, `neck_side_to_waist_bustpoint_f`, `neck_back_to_waist_b`, `across_back_b`, `across_chest_f`, `waist_to_hip_side`) and per-pair analysis showed the "dpm wins" choice is wrong for at least three (`bust_circ` anchors the Aldrich size chart, `across_back_b` / `across_chest_f` use Aldrich's reproducible fixed offsets).

**Decision:** emit **one `.smis` per drafting system, no mixing**.

- `aldrich.smis` — 21 `aldrich_*` entries + the 3 `aldrich_size_chart_p13.yaml` standard values (`dart_width_bust`, `armscye_length`, `waist_to_hip_side`) + the 2 Seamly-compat helpers (`bustpoint_to_waist`, `bustpoint_to_shoulder_center`). Template base: `references/seamly/samples/aldrich_women_template.smis`. Keep its 7 custom `@M_*` slots, but rewrite the @M_1 / @M_2 formulas to reference declared standard slots (`bustpoint_to_shoulder_center + bustpoint_to_waist` for @M_1; `height_waist_back - height_knee` for @M_2) — the original `@M_J10` / `@M_A23` refs are dangling (not declared in the template's `<body-measurements>` block).
- `dpm.smis` — 32 `dpm_bodice_*` + 5 `dpm_sleeve_*` + 14 `dpm_pants_*` + the 2 Seamly-compat helpers. Template base: `references/seamly/samples/all_measurements_template.smis`. No custom @M_* slots needed.

Each file fills shared Seamly slots (`bust_circ` etc.) from its own system's measurement. No conflict resolution.

**Implementation deferred to Phase 6** (when the scanner actually produces values). At that point:

- Rewrite `scripts/export_seamlyme.py` to take `--system aldrich|dpm`, drop the prefix-rank logic, filter entries by `name.startswith("aldrich_") or unprefixed` vs `name.startswith("dpm_") or unprefixed`, emit one `.smis` per call.
- Decide template-selection: hard-code per system, or accept `--template <path>`.
- Open: should the dpm `.smis` include the 3 `aldrich_size_chart_p13` standard values (`dart_width_bust`, `armscye_length`, `waist_to_hip_side`)? dpm bodice video doesn't define these; dpm drafts them as construction lines, not body measurements. Provisional: leave dpm's slots empty so SeamlyMe falls back to its formula defaults.

## Cross-cutting notes for the next session

- **The user works in caveman mode** (default level: `full`). Drop articles, fragments OK, short synonyms. Code, commits, and longer docs (like this one) go in normal prose.
- **Git config**: local repo uses `yaiza.alt@gmail.com` for commits; global name `Yaiza Gonzalo Alt` is fine.
- **LFS** is on, tracking `references/*.pdf` and `references/**/frame_*.jpg`. `.gitattributes` lives at repo root.
- **`.claude/`, `data/`, `.venv/`, `review.html`, frame audio + source videos** are gitignored.
- **Stray Scanner**: not validated against a real capture yet. Validate when iPhone is available.
- **6th edition Aldrich**: resolved. `aldrich_low_waist` updated to 5cm. 6th-ed photos in `references/aldrich/`. See "Source material coverage → Aldrich" for full edition diff.

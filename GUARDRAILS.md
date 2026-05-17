# AI Guardrails for the Body Scanner Project

This document defines what AI coding assistants may and may not generate while working on this project. It is part of the project spec; treat it with the same authority as `SPEC.md`.

Why this exists: AI is excellent at generating plausible code and plausible-sounding domain knowledge. In this project, plausible-but-wrong content has expensive consequences. A wrong SMPL-X vertex ID propagates into every measurement. A wrong Aldrich formula produces a block that doesn't fit, discovered only at toile-fitting time. Wrong library API calls produce code that runs but fits incorrectly. These guardrails exist to make those failures impossible at the source.

## 1. Three Categories of AI Generation

### 1.1 FREE

AI may generate without external grounding. Apply normal code review.

- File I/O, glue code, CLI wrappers
- SQLite schemas and queries
- Jinja templates
- Standard Open3D operations (TSDF fusion, mesh cleanup, point cloud rendering) — but verify import paths
- Standard PyTorch boilerplate
- SVG plumbing (rendering paths, exporting files)
- Test scaffolding
- Type hints, docstrings, project structure

### 1.2 RISKY

AI may generate, but must be grounded in a verifiable source provided in the session. Output requires verification before commit.

- Library APIs that change frequently. Before generating any code using these, fetch the current README/docs into the session:
  - `smplx` Python package
  - `potpourri3d` (heat-method geodesics)
  - RobustVideoMatting, SAM2, or whichever segmentation library
  - Open3D (less volatile but verify TSDF parameters against current docs)
- SMPL-X fitting code: must follow SMPLify-X conventions (https://github.com/vchoutas/smplify-x). Fetch the reference implementation before generating.
- Constructional line rules in `construct/lines.py`: code is fine; the *rules* themselves (where the side seam goes, how the apex is located) are human decisions documented in `references/construction_rules.md`.
- ARKit code (Phase 10): verify against Apple's current sample code, not training-data memory.

### 1.3 FORBIDDEN

AI must not generate the content from memory. These must come from source materials provided in the session.

- Aldrich measurement definitions: must be transcribed from the book pages in `references/aldrich_*.pdf`. Each entry in `measure/definitions/merged.yaml` requires a `source` field citing the page.
- dresspatternmaking.com measurement definitions: from `references/dpm_worksheet.png` and `references/dpm_upper_bust_photo.png`. Each entry cites the worksheet item.
- SMPL-X vertex IDs claimed as anatomical landmarks (apex, suprasternal notch, C7, etc.): proposed candidates only, requiring visual verification in Blender by the user. Verified IDs go into `references/smplx_vertex_landmarks.md`; raw audit trail (per-landmark confirmed/corrected/mirrored status) in `references/smplx_landmark_review.json`.
- Aldrich drafting formulas (Phase 9): transcribed from `references/aldrich_drafting_ch1.pdf`. Each formula in code requires a comment with the page number.
- Physical measurement values: only the user with a tape measure produces these. AI does not invent calibration targets.

## 2. Prompting Rules

When asking AI for code touching Risky or Forbidden territory, the prompt must include:

1. The relevant source material as context (book pages pasted as text, library README fetched, prior notes referenced).
2. An explicit instruction: *"If you cannot find this in the provided source material, say so. Do not infer or fill in plausibly."*
3. A request for source attribution: *"Each definition/formula in the output must have a comment naming the source page or section."*

If AI generates content without source attribution where attribution was requested, treat the output as suspect. Verify against the actual source before using.

## 3. SMPL-X Vertex Landmark Guardrail

SMPL-X has 10475 vertices. AI often produces vertex IDs that are plausible-sounding (round numbers, claimed-anatomical names) but wrong. Wrong vertex IDs cause every downstream measurement to drift, often by a few centimeters, in ways that are hard to debug.

**Rule: never commit a vertex ID to YAML or code without visually verifying it in Blender.**

Workflow:

1. AI proposes vertex IDs algorithmically (one-off Open3D / Blender helpers — see git history pre-TailorTwin rename for `scripts/propose_smplx_landmarks.py` and `scripts/blender_landmark_review.py`)
2. User opens the T-posed SMPL-X mesh in Blender (SMPL-X addon, v1.1 model), selects each proposed vertex via the N-panel UI, and confirms, corrects, or skips
3. Right-side landmarks auto-mirrored from verified left-side picks (X→−X nearest-vertex)
4. Results saved to `references/smplx_landmark_review.json` (audit trail with per-landmark status: confirmed / corrected / mirrored_from_X / skipped)
5. Verified IDs flow into `references/smplx_vertex_landmarks.md` (Verified column)

Screenshots no longer required as routine documentation — the interactive review session is the verification. Add screenshots only for spot-checks if a specific landmark is later questioned.

Authoritative sources for SMPL-X vertex semantics:
- `smplx` package's `vertex_ids.py`
- MeshCapade documentation
- Published research papers using SMPL-X for body measurement

When in doubt: verify in Blender. The cost of a Blender check (~2 minutes) is much less than the cost of debugging a 2cm measurement drift later.

## 4. SMPL-X Fitting Guardrail

SMPL-X fitting has many published implementations, each with subtly different conventions: axis order (y-up vs z-up), joint indexing, pose parameterization (axis-angle vs rotation-matrix vs 6D), regularizer weights, optimizer settings. AI often blends conventions across implementations, producing code that runs, converges, and looks plausible but fits incorrectly.

**Rules:**

- Treat SMPLify-X (https://github.com/vchoutas/smplify-x) as the authoritative reference. When generating fitting code, have AI fetch SMPLify-X's `fit_single_frame.py` or equivalent into the session and follow its conventions.
- Validate fits visually before trusting them. Render the SMPL-X mesh and the scan point cloud in the same coordinate system with the same axes. Misaligned axes are the most common silent failure mode.
- The distance heatmap check (Phase 4 Stage C) is mandatory before trusting any fit for measurement extraction.
- If a fit looks reasonable but extracted measurements are systematically off after calibration, suspect the fitting code before the measurement code. Specifically: check axis conventions, joint ordering, and pose parameterization.

## 5. Measurement Definition Guardrail

Every measurement entry in `src/tailor_twin/measure/definitions/merged.yaml` must have a `source` field. No exceptions.

If an entry lacks a source, do one of:

1. Find the source and add it (e.g. "Aldrich p.179 instruction #5")
2. If no source exists in the reference books, treat it as user-invented: add a `notes` field explaining the rationale and accept that this measurement has no external validation
3. Delete the entry

AI-suggested entries pass this filter only after the user has manually checked the source matches the claim. AI may propose entries; the user verifies.

## 6. Drafting Formula Guardrail (Phase 9)

Aldrich's drafting formulas are precise: front armhole depth as a function of bust size, neck width as a fraction, dart positions, ease allowances. AI generating these from memory will produce formulas that look right (right shape, plausible coefficients) and are wrong. Wrong drafting formulas produce blocks that don't fit, and the failure mode is only visible at toile stage.

**Rules:**

- Photograph or scan the relevant Aldrich pages for each block (bodice, skirt, sleeve) into `references/aldrich_drafting_ch1.pdf`
- Paste the relevant page text/images into the AI session when asking for code
- Each formula in `blocks/aldrich_*.py` must have a comment with the page reference
- Cross-check: pick two or three numerical outputs from generated code for a known set of measurements, compute them by hand from the book, confirm they match before trusting the code at scale

## 7. Red Flags

Stop and verify when:

- AI confidently provides specific SMPL-X vertex indices without you having loaded a reference document into the session
- AI cites a paper, repo, or function name with specific details (line numbers, function signatures) you haven't shown it
- AI's formula uses a constant or coefficient that wasn't in your source material
- Generated code uses an import path or class name that doesn't appear in the library's current documentation
- "This should work" appears without a way to test that it does
- A "standard convention" is invoked for something where multiple conventions exist (axis order, rotation representation, etc.)

Each of these is recoverable, but cheaper to catch at code-review time than at calibration or fitting time.

## 8. Where AI Is Genuinely Useful

To be balanced: AI is a real productivity multiplier on this project when used correctly. Effective roles:

- **Fast typist** for code you've designed
- **Rubber duck** for debugging (paste error + relevant code, get hypotheses)
- **Translator** between domains ("here's an Aldrich formula in English, write it as NumPy")
- **Reviewer** of YAML definitions ("does this entry look consistent with the worksheet image?")
- **Doc reader** ("fetch the current potpourri3d docs and summarize the heat-method API")
- **Visualization helper** (Open3D / matplotlib code for inspection plots)
- **Refactorer** of code you wrote, given clear constraints

## 9. Where AI Is Not the Right Tool

Don't use AI for:

- Domain expert on pattern drafting (use the source books)
- Memory for SMPL-X vertex semantics (verify in Blender)
- Independent source of measurement formulas (use the source books)
- Judge of whether a SMPL-X fit is "good enough" (visual inspection + distance heatmap)
- Substitute for taking your own tape measurements (only you can do this)

## 10. Enforcement

These guardrails are enforced by:

1. The `source` field in `merged.yaml` (Section 5)
2. The `references/smplx_vertex_landmarks.md` file + `references/smplx_landmark_review.json` audit trail (Section 3)
3. Comments in `blocks/aldrich_*.py` citing page numbers (Section 6)
4. Visual verification at Phase 4 (fitting) and Phase 5 (constructional lines)
5. Tape measurement calibration at Phase 7

If any of these enforcement mechanisms is missing or empty for a piece of code, that code is not trustworthy regardless of how plausible it looks.

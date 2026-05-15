# Continuation prompt

Paste this into a fresh Claude Code session to resume the body-scanner
project.

---

I'm resuming a personal LiDAR-based body-scanner project for sewing-pattern
drafting. Read these three files first, in order:

1. @SPEC.md — authoritative project spec
2. @GUARDRAILS.md — AI-generation rules (FREE / RISKY / FORBIDDEN)
3. @SESSION_STATE.md — last session's state and where I am right now

Project context in one paragraph: iPhone Pro LiDAR captures the body via
Stray Scanner → AirDrop to Mac → Python pipeline (segment, TSDF fuse, fit
SMPL-X+D, extract ~45 measurements across the Aldrich and
dresspatternmaking.com systems, export to SeamlyMe `.smis` and a populated
worksheet). Single-user, local-only, female-target. Python 3.12.13 pinned
(Open3D 0.19 wheel cap). 72 measurement definitions live in
@src/body_scanner/measure/definitions/merged.yaml, each with sources,
notes, a `seamly_name` cross-walk, and (for the high-value 14) verified
frame citations. Phase 0 is done; Phase 1 has a Stray-loader skeleton that
needs validation against a real capture; Phase 6 is mid-flight (definitions
populated, code not written).

How we work:

- I use **caveman mode** at level `full`. Drop articles, fragments OK,
  short synonyms. Code, commits, and longer docs go in normal prose. Don't
  add emojis.
- **Guardrails are strict.** Aldrich and dpm measurement definitions are
  FORBIDDEN-from-AI-memory territory — they must come from the source
  files in `references/`. Every `merged.yaml` entry has a `sources` field
  for that reason. Don't generate vertex IDs, drafting formulas, or
  measurement definitions from memory. Stop and ask if you don't have the
  source in the session.
- For risky library APIs (smplx, potpourri3d, SAM2, ARKit), fetch the
  current README/docs into the session before generating code.
- Local git config uses email `yaiza.alt@gmail.com`. Commit with that
  identity.
- LFS is on; renames preserve LFS pointers.

What's most likely worth doing next (pick one or ask me which):

A. **Validate Seamly cross-walk against the full catalog.** This session
   the user added @references/seamly/ — extracted from Seamly2D's `develop`
   branch (commit `8b6bc512a9`). It includes a 262-name catalog in
   `references/seamly/README.md`, XSD schemas in `references/seamly/schema/`,
   107 SVG diagrams keyed by group code in `references/seamly/diagrams/`,
   and an `aldrich_women_template.smis` sample. Verify every `seamly_name`
   in `merged.yaml` exists in the catalog; check whether the
   Aldrich-flavoured template's conventions (`@M_1..@M_7` custom slots,
   named-string measurements like "Front Shoulder to Waist", "Waist to
   Knee") should change my mappings or the exporter.

B. **Embed Seamly diagrams in the review page.** `scripts/generate_review_html.py`
   already shows each entry's `seamly_name` as a green chip. The next step
   is to map `seamly_name` → diagram group code (from the table in
   `references/seamly/README.md`) → inline the matching SVG
   (`references/seamly/diagrams/<Group>p<n>.svg`) so each card shows the
   Seamly visual reference alongside dpm frames.

C. **XSD-validate the exporter output.** Make
   `scripts/export_seamlyme.py` validate generated `.smis` files against
   `references/seamly/schema/individual_measurements_v0.3.4.xsd` (use
   `lxml` if it isn't blocked by deps; otherwise document the validation
   command).

D. **6th-edition Aldrich migration.** I own the 6th edition physically;
   the PDF in repo is 5th edition. SESSION_STATE.md lists the diffs. Open
   question: confirm the low-waist offset (5 cm vs 6 cm) in 6th-edition
   item 2a so I can decide whether to update `aldrich_low_waist`.

E. **Wait for Stray Scanner capture.** Once I have a real capture, the
   loader skeleton in @src/body_scanner/io/stray_loader.py needs to be
   validated against the actual on-disk format. There are documented open
   questions in the module docstring.

F. **Phase 8 scaffolding.** SQLite schema + Jinja worksheet template are
   FREE territory and don't depend on anything in flight. Could be useful
   to scaffold so Phase 6 has somewhere to write to.

I'll tell you which one to pick — or propose your own based on what
SESSION_STATE.md says. Don't write code until I confirm.

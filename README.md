# body-scanner

Personal LiDAR-based body scanner for sewing pattern drafting. Captures body
geometry with an iPhone/iPad Pro LiDAR sensor, reconstructs a mesh, fits an
SMPL-X+D parametric body model, and extracts the ~45 measurements needed to
draft Aldrich and dresspatternmaking.com blocks.

See [`SPEC.md`](SPEC.md) for the authoritative project specification, and
[`GUARDRAILS.md`](GUARDRAILS.md) for the AI-generation rules that govern how
this repo is built. The kickoff prompt lives in `PROMPT.md` when present.

This is a personal, single-user, local-only project. No cloud, no auth, no
shared backend.

"""body_scanner — personal LiDAR body-scanning pipeline.

See SPEC.md for the project specification and GUARDRAILS.md for AI-generation
rules. The package is organised into subpackages mirroring the pipeline:

    io/          capture loaders (Stray Scanner, custom iOS)
    preprocess/  segmentation, depth filtering
    reconstruct/ TSDF fusion, mesh cleanup
    fit/         SMPL-X+D fitting and landmarks
    construct/   constructional lines on the fitted mesh
    measure/     measurement extractor + YAML definitions
    blocks/      (Phase 9) drafting block generators
    viz/         viewers, HTML worksheet
    storage/     SQLite + OBJ export
"""

__version__ = "0.0.1"

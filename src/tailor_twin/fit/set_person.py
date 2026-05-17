"""CLI: patch subject identity fields onto an existing fit npz.

Usage:
    python -m tailor_twin.fit.set_person <fit_npz> \
        --given-name Oscar --family-name "" --birth-date 1990-01-01

Rewrites the npz in place, preserving every other key. Avoids re-fitting
just to fill the <personal> block.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("fit_npz", type=Path)
    p.add_argument("--given-name", default=None)
    p.add_argument("--family-name", default=None)
    p.add_argument("--birth-date", default=None)
    p.add_argument("--gender", default=None,
                   help="Overwrite stored gender (female/male/neutral).")
    args = p.parse_args(argv)

    src = np.load(args.fit_npz, allow_pickle=True)
    patched: dict = {k: src[k] for k in src.files}
    if args.given_name is not None:
        patched["person_given_name"] = np.array(args.given_name)
    if args.family_name is not None:
        patched["person_family_name"] = np.array(args.family_name)
    if args.birth_date is not None:
        patched["person_birth_date"] = np.array(args.birth_date)
    if args.gender is not None:
        patched["gender"] = np.array(args.gender)
    np.savez(args.fit_npz, **patched)
    print(f"patched {args.fit_npz}: "
          f"given={patched.get('person_given_name')} "
          f"family={patched.get('person_family_name')} "
          f"birth={patched.get('person_birth_date')} "
          f"gender={patched.get('gender')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

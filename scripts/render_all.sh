#!/usr/bin/env bash
# Drive scripts/render_measurement_review.py in small parallel batches.
# Kaleido crashes after ~5 renders so each subprocess does just BATCH codes.
# Resumes — skips codes whose data/review/<code>/ already has 5 PNGs.

set -u
FIT="${1:-data/results/yaiza_smplx_fit.npz}"
PARALLEL="${2:-4}"
PY=.venv/bin/python
BATCH=2

$PY -c '
from pathlib import Path
from body_scanner.measure.seamly_catalog import RECIPES
root = Path("data/review")
remaining = []
for c in sorted(RECIPES.keys()):
    d = root / c
    pngs = list(d.glob("*.png")) if d.is_dir() else []
    if len(pngs) < 5:
        remaining.append(c)
print("\n".join(remaining))
' > /tmp/codes.txt

total=$(wc -l < /tmp/codes.txt | tr -d " ")
echo "codes to render: $total (parallel=$PARALLEL, batch=$BATCH)"

mapfile -t codes < /tmp/codes.txt

# Group into batches of $BATCH codes per line.
> /tmp/batches.txt
i=0
while (( i < ${#codes[@]} )); do
  batch=("${codes[@]:$i:$BATCH}")
  echo "${batch[*]}" >> /tmp/batches.txt
  i=$((i + BATCH))
done

# Run N subprocesses in parallel.
cat /tmp/batches.txt | xargs -n 1 -P "$PARALLEL" -I {} bash -c \
  '.venv/bin/python scripts/render_measurement_review.py "'"$FIT"'" --codes $0 >> /tmp/render.log 2>&1' {}

echo "DONE"

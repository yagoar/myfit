#!/usr/bin/env bash
#
# ingest_video.sh — extract audio from a dpm measurement video and transcribe
# it with whisper.cpp. Output is a timestamped transcript that becomes the
# citable source for dpm measurement definitions in merged.yaml.
#
# Source policy: dpm measurement definitions are FORBIDDEN from AI memory
# (GUARDRAILS section 1.3). This script produces the on-disk source files
# that the YAML "source" fields will cite, e.g.
#   source: "references/dpm_videos/upper_bust/transcript.txt:00:42"
#
# Dependencies:
#   brew install ffmpeg whisper-cpp
#   Model files downloaded once into ~/.local/share/whisper-cpp/ (see below).
#
# Usage:
#   scripts/ingest_video.sh <video_file> <measurement_name> [model]
#
# Example:
#   scripts/ingest_video.sh ~/Downloads/upper_bust.mp4 upper_bust
#   scripts/ingest_video.sh ~/Downloads/bust_span.mov bust_span small.en
#
# Output layout:
#   references/dpm_videos/<measurement_name>/
#     source.mp4         (symlink to the input video, for provenance)
#     audio.wav          (16kHz mono, whisper-cpp input)
#     transcript.txt     (plain text)
#     transcript.srt     (timestamped)

set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "usage: $0 <video_file> <measurement_name> [model]" >&2
  exit 2
fi

VIDEO="$1"
NAME="$2"
MODEL_NAME="${3:-base.en}"

if [[ ! -f "$VIDEO" ]]; then
  echo "error: video file not found: $VIDEO" >&2
  exit 1
fi

# Locate the repo root (this script is in repo/scripts/)
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT_DIR="$REPO_ROOT/references/dpm_videos/$NAME"
MODEL_DIR="${WHISPER_MODEL_DIR:-$HOME/.local/share/whisper-cpp}"
MODEL_FILE="$MODEL_DIR/ggml-$MODEL_NAME.bin"

# Sanity-check deps
for bin in ffmpeg whisper-cli; do
  if ! command -v "$bin" >/dev/null 2>&1; then
    echo "error: missing dependency '$bin'." >&2
    echo "       brew install ffmpeg whisper-cpp" >&2
    exit 1
  fi
done

mkdir -p "$OUT_DIR" "$MODEL_DIR"

# Download the model on first use. whisper.cpp ships a helper script for this
# but downloading directly from huggingface is more reliable across versions.
if [[ ! -f "$MODEL_FILE" ]]; then
  echo "downloading whisper model '$MODEL_NAME' (one-time)..." >&2
  curl -fL --progress-bar \
    -o "$MODEL_FILE" \
    "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-$MODEL_NAME.bin"
fi

# Preserve provenance: symlink the original video alongside the transcript.
# Symlink rather than copy so we don't bloat the repo. The actual video lives
# wherever the user keeps it.
ln -sf "$VIDEO" "$OUT_DIR/source$(echo "$VIDEO" | sed -n 's/.*\(\.[^.]\+\)$/\1/p')"

# Extract audio: whisper expects 16kHz mono PCM.
echo "extracting audio..." >&2
ffmpeg -y -loglevel error \
  -i "$VIDEO" \
  -ac 1 -ar 16000 -vn \
  "$OUT_DIR/audio.wav"

# Transcribe. -otxt + -osrt write both plain and timestamped outputs.
echo "transcribing with whisper-cli ($MODEL_NAME)..." >&2
whisper-cli \
  -m "$MODEL_FILE" \
  -f "$OUT_DIR/audio.wav" \
  -otxt -osrt \
  -of "$OUT_DIR/transcript" \
  >/dev/null

echo "done." >&2
echo "  transcript: $OUT_DIR/transcript.txt"
echo "  timestamps: $OUT_DIR/transcript.srt"

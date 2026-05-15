#!/usr/bin/env bash
#
# ingest_video.sh — ingest a dpm measurement video and produce citable sources.
#
# Inputs may be either a local video file or a URL that yt-dlp can fetch.
# Output is a per-measurement folder containing:
#   * transcript.txt  / transcript.srt  (whisper.cpp, citable as :timestamp)
#   * frame_HHMMSS.jpg                  (periodic frames; align with .srt)
#   * audio.wav                         (16kHz mono, intermediate)
#   * source.<ext>                      (symlink/copy of the source video)
#
# Source policy: dpm measurement definitions are FORBIDDEN from AI memory
# (GUARDRAILS section 1.3). The transcripts and frames produced here become
# the on-disk source cited in merged.yaml `source:` fields, e.g.
#   source: "references/dpm_videos/upper_bust/transcript.srt:00:42"
#   source: "references/dpm_videos/upper_bust/frame_000042.jpg"
#
# Dependencies (one-time):
#   brew install ffmpeg whisper-cpp yt-dlp
#
# Usage:
#   scripts/ingest_video.sh <video_or_url> <subpath> [opts]
#
# <subpath> is a folder name relative to references/. Output lands in
#   references/<subpath>/. Convention: a single dpm_videos/ root holds both
#   measurement-taking videos and drafting tutorials, distinguished by the
#   <topic> name. See SPEC.md section 5 for the dual-role policy.
#     dpm_videos/bodice_measurements   — measurement-taking video
#     dpm_videos/bodice_front          — drafting tutorial (front bodice)
#     dpm_videos/pants_1               — drafting tutorial (pants part 1)
#
# Options (env vars, override defaults):
#   FRAME_INTERVAL   seconds between extracted frames (default: 3, 0 disables)
#   WHISPER_MODEL    whisper.cpp model name (default: base.en)
#   YTDLP_COOKIES    pass to yt-dlp --cookies-from-browser (e.g. "chrome")
#
# Examples:
#   scripts/ingest_video.sh ~/Downloads/upper_bust.mp4 dpm_videos/upper_bust
#   scripts/ingest_video.sh https://youtu.be/XXXX dpm_videos/bodice_measurements
#   scripts/ingest_video.sh https://youtu.be/YYYY dpm_videos/bodice_front
#   FRAME_INTERVAL=5 scripts/ingest_video.sh ./vid.mov dpm_videos/dart
#   YTDLP_COOKIES=chrome scripts/ingest_video.sh https://dpm.example/v hips

set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "usage: $0 <video_or_url> <subpath>" >&2
  echo "  <subpath> is relative to references/ (e.g. dpm_videos/upper_bust)" >&2
  echo "  env: FRAME_INTERVAL=<sec> WHISPER_MODEL=<name> YTDLP_COOKIES=<browser>" >&2
  exit 2
fi

INPUT="$1"
SUBPATH="$2"
FRAME_INTERVAL="${FRAME_INTERVAL:-3}"
MODEL_NAME="${WHISPER_MODEL:-base.en}"

# Reject absolute or upward subpaths — output must stay under references/.
case "$SUBPATH" in
  /*|*..*) echo "error: subpath must be relative and stay under references/" >&2; exit 2 ;;
esac

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT_DIR="$REPO_ROOT/references/$SUBPATH"
MODEL_DIR="${WHISPER_MODEL_DIR:-$HOME/.local/share/whisper-cpp}"
MODEL_FILE="$MODEL_DIR/ggml-$MODEL_NAME.bin"

# Sanity-check deps (yt-dlp only required for URLs)
for bin in ffmpeg whisper-cli; do
  if ! command -v "$bin" >/dev/null 2>&1; then
    echo "error: missing dependency '$bin'." >&2
    echo "       brew install ffmpeg whisper-cpp yt-dlp" >&2
    exit 1
  fi
done

mkdir -p "$OUT_DIR" "$MODEL_DIR"

# Resolve INPUT to a local file. If it looks like a URL, download via yt-dlp.
if [[ "$INPUT" =~ ^https?:// ]]; then
  if ! command -v yt-dlp >/dev/null 2>&1; then
    echo "error: yt-dlp not installed (needed for URL inputs)." >&2
    echo "       brew install yt-dlp" >&2
    exit 1
  fi
  echo "downloading via yt-dlp..." >&2
  YTDLP_ARGS=(-o "$OUT_DIR/source.%(ext)s" --no-playlist)
  if [[ -n "${YTDLP_COOKIES:-}" ]]; then
    YTDLP_ARGS+=(--cookies-from-browser "$YTDLP_COOKIES")
  fi
  yt-dlp "${YTDLP_ARGS[@]}" "$INPUT"
  # Find what yt-dlp wrote (extension chosen by site).
  VIDEO_FILE="$(ls -1 "$OUT_DIR"/source.* 2>/dev/null | grep -v '\.srt$\|\.txt$\|\.wav$\|\.jpg$' | head -n1)"
  if [[ -z "$VIDEO_FILE" ]]; then
    echo "error: yt-dlp finished but no source.* file present." >&2
    exit 1
  fi
else
  if [[ ! -f "$INPUT" ]]; then
    echo "error: video file not found: $INPUT" >&2
    exit 1
  fi
  # Preserve provenance via symlink (don't bloat repo)
  EXT=".$(echo "$INPUT" | sed -n 's/.*\.\([^.]\+\)$/\1/p')"
  VIDEO_FILE="$OUT_DIR/source$EXT"
  ln -sf "$INPUT" "$VIDEO_FILE"
fi

# Download whisper model on first use
if [[ ! -f "$MODEL_FILE" ]]; then
  echo "downloading whisper model '$MODEL_NAME' (one-time)..." >&2
  curl -fL --progress-bar \
    -o "$MODEL_FILE" \
    "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-$MODEL_NAME.bin"
fi

# Extract audio: whisper expects 16kHz mono PCM
echo "extracting audio..." >&2
ffmpeg -y -loglevel error \
  -i "$VIDEO_FILE" \
  -ac 1 -ar 16000 -vn \
  "$OUT_DIR/audio.wav"

# Transcribe (plain + timestamped)
echo "transcribing with whisper-cli ($MODEL_NAME)..." >&2
whisper-cli \
  -m "$MODEL_FILE" \
  -f "$OUT_DIR/audio.wav" \
  -otxt -osrt \
  -of "$OUT_DIR/transcript" \
  >/dev/null

# Extract periodic frames. Naming uses elapsed time (HHMMSS) so the file order
# matches the .srt timeline visually.
if [[ "$FRAME_INTERVAL" -gt 0 ]]; then
  echo "extracting frames every ${FRAME_INTERVAL}s..." >&2
  # %{pts}: presentation timestamp; format as HHMMSS via strftime
  ffmpeg -y -loglevel error \
    -i "$VIDEO_FILE" \
    -vf "fps=1/$FRAME_INTERVAL" \
    -frame_pts 1 \
    -q:v 3 \
    "$OUT_DIR/frame_%06d.jpg"
fi

# Compact summary so the user sees what was produced
FRAME_COUNT=$(find "$OUT_DIR" -maxdepth 1 -name 'frame_*.jpg' | wc -l | tr -d ' ')
echo "done."
echo "  transcript: $OUT_DIR/transcript.txt"
echo "  timestamps: $OUT_DIR/transcript.srt"
echo "  frames:     $FRAME_COUNT in $OUT_DIR/"

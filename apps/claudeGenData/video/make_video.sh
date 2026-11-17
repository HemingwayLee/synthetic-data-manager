#!/usr/bin/env bash
# Build out/tutorial-ja.mp4: narration with macOS `say`, then recording and rendering in Docker.
# Usage: ./make_video.sh [--voice Kyoko] [--rate 200]
set -euo pipefail
cd "$(dirname "$0")"

python3 tts.py "$@"
docker compose run --rm video

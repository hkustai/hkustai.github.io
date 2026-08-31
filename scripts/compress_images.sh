#!/usr/bin/env bash
# Build members/images/ from members/originals/ (quality-first JPEG).
# Then refresh group.html and the side-by-side preview.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

python3 "$ROOT/scripts/optimize_avatars.py"
python3 "$ROOT/scripts/render_members.py"
python3 "$ROOT/scripts/preview_avatars.py"

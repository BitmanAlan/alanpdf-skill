#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

python3 "$ROOT_DIR/scripts/alanpdf.py" \
  --input "$ROOT_DIR/examples/proposal/harborgrid-platform.md" \
  --output "$ROOT_DIR/examples/proposal/harborgrid-platform.pdf"

python3 "$ROOT_DIR/scripts/alanpdf.py" \
  --input "$ROOT_DIR/examples/pricing-memo/astera-ai-enablement.md" \
  --output "$ROOT_DIR/examples/pricing-memo/astera-ai-enablement.pdf"

python3 "$ROOT_DIR/scripts/alanpdf.py" \
  --input "$ROOT_DIR/examples/equity-report/novaforge-robotics.md" \
  --output "$ROOT_DIR/examples/equity-report/novaforge-robotics.pdf"

echo "Rendered all example PDFs."

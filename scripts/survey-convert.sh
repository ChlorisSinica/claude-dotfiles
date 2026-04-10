#!/usr/bin/env bash
# survey-convert.sh
# Usage: bash ~/.claude/scripts/survey-convert.sh [input.md] [output.tex]
#
# Converts a Markdown survey draft to LaTeX using Pandoc.
# Default: .claude/context/draft.md → output/survey.tex

set -euo pipefail

INPUT="${1:-.claude/context/draft.md}"
OUTPUT="${2:-output/survey.tex}"
OUTPUT_DIR="$(dirname "$OUTPUT")"
BIB_FILE="${OUTPUT_DIR}/references.bib"

# Check Pandoc
if ! command -v pandoc &>/dev/null; then
    echo "ERROR: Pandoc is not installed." >&2
    echo "" >&2
    echo "Install Pandoc:" >&2
    echo "  Windows: winget install --id JohnMacFarlane.Pandoc" >&2
    echo "  macOS:   brew install pandoc" >&2
    echo "  Linux:   sudo apt install pandoc" >&2
    exit 1
fi

# Check input
if [[ ! -f "$INPUT" ]]; then
    echo "ERROR: Input file not found: $INPUT" >&2
    exit 1
fi

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Build Pandoc args
PANDOC_ARGS=(
    "$INPUT"
    -o "$OUTPUT"
    --standalone
    --wrap=none
)

# Add bibliography if .bib file exists
if [[ -f "$BIB_FILE" ]]; then
    PANDOC_ARGS+=(--citeproc "--bibliography=$BIB_FILE")
    echo "Using bibliography: $BIB_FILE"
fi

echo "Converting: $INPUT → $OUTPUT"
pandoc "${PANDOC_ARGS[@]}"

echo ""
echo "=== Done ==="
echo "  Output: $OUTPUT"
[[ -f "$BIB_FILE" ]] && echo "  Bibliography: $BIB_FILE"
echo ""
echo "To compile:"
echo "  cd $OUTPUT_DIR && pdflatex survey && bibtex survey && pdflatex survey && pdflatex survey"

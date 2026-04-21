#!/usr/bin/env python3
"""Convert a Markdown survey draft to LaTeX using Pandoc.

Usage:
    <python-launcher> ~/.claude/scripts/survey-convert.py [input.md] [output.tex]

Default: .claude/context/draft.md -> output/survey.tex
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert a Markdown survey draft to LaTeX using Pandoc.",
    )
    parser.add_argument(
        "input",
        nargs="?",
        default=".claude/context/draft.md",
        help="Input Markdown file (default: .claude/context/draft.md)",
    )
    parser.add_argument(
        "output",
        nargs="?",
        default="output/survey.tex",
        help="Output LaTeX file (default: output/survey.tex)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    input_path = Path(args.input)
    output_path = Path(args.output)
    output_dir = output_path.parent
    bib_file = output_dir / "references.bib"

    if shutil.which("pandoc") is None:
        sys.stderr.write(
            "ERROR: Pandoc is not installed.\n"
            "\n"
            "Install Pandoc:\n"
            "  Windows: winget install --id JohnMacFarlane.Pandoc\n"
            "  macOS:   brew install pandoc\n"
            "  Linux:   sudo apt install pandoc\n"
        )
        return 1

    if not input_path.is_file():
        sys.stderr.write(f"ERROR: Input file not found: {input_path}\n")
        return 1

    output_dir.mkdir(parents=True, exist_ok=True)

    pandoc_args = [
        "pandoc",
        str(input_path),
        "-o",
        str(output_path),
        "--standalone",
        "--wrap=none",
    ]

    if bib_file.is_file():
        pandoc_args.extend(["--citeproc", f"--bibliography={bib_file}"])
        print(f"Using bibliography: {bib_file}")

    print(f"Converting: {input_path} -> {output_path}")
    result = subprocess.run(pandoc_args)
    if result.returncode != 0:
        return result.returncode

    print()
    print("=== Done ===")
    print(f"  Output: {output_path}")
    if bib_file.is_file():
        print(f"  Bibliography: {bib_file}")
    print()
    print("To compile:")
    print(
        f"  cd {output_dir} && pdflatex survey && bibtex survey && pdflatex survey && pdflatex survey"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

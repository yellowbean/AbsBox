#!/usr/bin/env python
"""Export marimo notebooks for the Sphinx docs.

Notebooks live in ``docs/source/marimo/**/*.py``. Depending on ``--format``
this writes, under ``docs/source/_static/marimo/``:

* ``html`` (default): ``marimo export html`` executes the notebook and bakes
  the outputs into a static page (embed it with an ``<iframe>``).
* ``md``: ``marimo export md`` writes a Markdown file (MyST flavor by default).
* ``both``: both of the above.

The generated files are committed; readers never need Python, WASM, or the
``Hastructure`` engine. Re-run whenever a notebook changes::

    just export-marimo                 # html
    just export-marimo md              # markdown
    just export-marimo both            # html + markdown
    uv run python docs/export_marimo.py --format md --md-flavor pymdown

Embed an exported notebook (HTML) in any ``.rst`` page::

    .. raw:: html

       <iframe src="_static/marimo/example.html"
               style="width:100%; height:600px;" loading="lazy"></iframe>
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

DOCS = Path(__file__).resolve().parent
SRC = DOCS / "source" / "marimo"
OUT = DOCS / "source" / "_static" / "marimo"
FLAVORS = ("mystmd", "pymdown", "qmd", "mdx")


def _name(notebook: Path) -> str:
    return str(notebook.relative_to(SRC).with_suffix("")).replace("/", "_")


def _run(args: list[str]) -> None:
    subprocess.run([sys.executable, "-m", "marimo", *args], check=True)


def export_html(notebook: Path, include_code: bool = False) -> Path:
    out = OUT / f"{_name(notebook)}.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    args = ["export", "html", str(notebook), "-o", str(out), "--force"]
    if not include_code:
        args.append("--no-include-code")
    _run(args)
    return out


def export_md(notebook: Path, flavor: str = "mystmd") -> Path:
    out = OUT / f"{_name(notebook)}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    _run(["export", "md", str(notebook), "-o", str(out), "--force", "--flavor", flavor])
    return out


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--format", choices=("html", "md", "both"), default="html",
                        help="what to export (default: html)")
    parser.add_argument("--include-code", action="store_true",
                        help="include source cells in the HTML export")
    parser.add_argument("--md-flavor", default="mystmd", choices=FLAVORS,
                        help="Markdown flavor for the md export (default: mystmd)")
    args = parser.parse_args()

    notebooks = sorted(SRC.rglob("*.py"))
    if not notebooks:
        print(f"No notebooks found under {SRC}", file=sys.stderr)
        return 1

    for notebook in notebooks:
        if args.format in ("html", "both"):
            out = export_html(notebook, include_code=args.include_code)
            print(f"{notebook.relative_to(DOCS.parent)} -> {out.relative_to(DOCS.parent)}")
        if args.format in ("md", "both"):
            out = export_md(notebook, flavor=args.md_flavor)
            print(f"{notebook.relative_to(DOCS.parent)} -> {out.relative_to(DOCS.parent)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

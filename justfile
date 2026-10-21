# List every available recipe with its documentation.
default:
    @just --list

# Run engine regression tests against: local (default), dev, or prod (Singapore servers).
#   just regression        -> local engine (http://localhost:8081)
#   just regression dev    -> remote Singapore dev server
#   just regression prod   -> production stable server in Singapore
regression engine="local":
    echo "Running regression tests against {{engine}} engine"
    ABSBOX_TEST_SERVER={{engine}} uv run --extra test pytest absbox/tests/regression/test_main.py

# Bump the single source of truth. Sphinx docs derive their version from pyproject.toml.
update-version version:
    echo "Update Version: {{version}}"
    sed -i "s/^version = .*/version = \"{{version}}\"/g"  pyproject.toml
    uv lock

# Export marimo notebooks (docs/source/marimo/*.py). format: html (default), md, or both.
#   just export-marimo              -> static HTML (baked outputs)
#   just export-marimo md           -> Markdown (code-fenced, not executed)
#   just export-marimo both         -> both
#   just export-marimo md pymdown   -> Markdown with a specific flavor
export-marimo format="html" flavor="mystmd":
    uv run python docs/export_marimo.py --format {{format}} --md-flavor {{flavor}}

# Commit the version bump, create an annotated tag, and push it (env is a prefix, e.g. v).
tag env version:
    echo "Tagging"
    git add pyproject.toml uv.lock
    git commit -m "bump version to-> < {{version}} >"
    git tag -a {{env}}{{version}} -m "{{env}}{{version}}"
    git push origin HEAD --tag

# Delete a tag locally and from the remote.
untag version:
    echo "Untagging"
    git tag -d {{version}}
    git push --delete origin {{version}}

# Push the current HEAD and all tags.
push-tag:
    echo "Pushing Tag"
    git push origin HEAD --tag

# Push the current HEAD.
push-code:
    echo "Pushing Code"
    git push origin HEAD

# Build the docs with live reload (sphinx-autobuild).
live-doc:
    echo "Live Doc"
    sphinx-autobuild docs/source docs/build/html --open-browser --watch docs/source

# Preview the unreleased changelog (fragments in changes/) without writing files.
changelog-draft version:
    uvx towncrier build --draft --version {{version}}

# Fold changes/* fragments into CHANGELOG.rst for a release.
changelog-build version:
    uvx towncrier build --version {{version}}
    git add CHANGELOG.rst changes

# Release workflow: test, bump version, tag, and push (env is a prefix, e.g. v).
# The static code check (just code-inspect) runs first and stops everything on
# ruff-gate findings (mypy/pyright stay advisory and are recorded in the report).
publish env version:
    echo "Pushing to PyPI {{env}}"
    just code-inspect absbox
    just regression dev
    just update-version {{version}}
    just tag {{env}} {{version}}
    just push-code

# Local static-analysis scan mirroring the CI advisory stack (#51):
#   ruff (repo gate rules), mypy + pyright (advisory).
# Writes a findings report to `<git short hash>_code_inspect.md` in the repo root.
#   just code-inspect              -> scan absbox with default pyright pin
#   just code-inspect absbox 1.1.405
# Exit: 0 = ruff gate clean (advisory findings don't matter); 1 = ruff findings;
#       2 = ruff could not run. `publish` calls this first and stops on nonzero.
# NixOS note: the bundled ruff/pyright binaries die on stub-ld; the recipe
# patches a throwaway ruff copy with the nix glibc loader (/tmp/absbox-tools)
# and runs pyright through nix node (`npx pyright`).
code-inspect target="absbox" pyrightVersion="1.1.405":
    #!/usr/bin/env bash
    set -uo pipefail

    HASH=$(git rev-parse --short HEAD)
    OUT="${HASH}_code_inspect.md"
    TMP=$(mktemp -d /tmp/absbox-inspect.XXXXXX)
    trap 'rm -rf "$TMP"' EXIT
    RUFF_LOG="$TMP/ruff.log"; MYPY_LOG="$TMP/mypy.log"; PYRIGHT_LOG="$TMP/pyright.log"

    PY=".venv/bin/python"; [ -x "$PY" ] || PY=python3
    ANNOT="$PY tools/annotate_from_log.py"

    prep_ruff() {
        if ruff --version >/dev/null 2>&1; then echo "ruff"; return 0; fi
        FIXED=/tmp/absbox-tools/ruff
        if [ ! -x "$FIXED" ] || ! "$FIXED" --version >/dev/null 2>&1; then
            mkdir -p /tmp/absbox-tools
            if [ ! -f .venv/bin/ruff ]; then return 1; fi
            cp .venv/bin/ruff "$FIXED" || return 1
            nix-shell --packages patchelf glibc --run \
              'patchelf --set-interpreter "$(ls /nix/store/*glibc-*/lib/ld-linux-x86-64.so.2 | head -1)" --set-rpath "$(ls -d /nix/store/*glibc-*/lib | head -1)" /tmp/absbox-tools/ruff' \
              >/dev/null 2>&1 || return 1
        fi
        "$FIXED" --version >/dev/null 2>&1 && { echo "$FIXED"; return 0; }
        return 1
    }

    if RUFF_BIN=$(prep_ruff); then
        "$RUFF_BIN" check --output-format concise --no-cache {{target}} >"$RUFF_LOG" 2>&1
        RUFF_EXIT=$?
        RUFF_VER=$("$RUFF_BIN" --version 2>/dev/null | head -1)
    else
        echo "ruff unavailable on this system (no runnable binary)" > "$RUFF_LOG"
        RUFF_EXIT=-1
        RUFF_VER="skipped"
    fi

    "$PY" -m mypy >"$MYPY_LOG" 2>&1
    MYPY_EXIT=$?

    if pyright --version >/dev/null 2>&1; then
        pyright >"$PYRIGHT_LOG" 2>&1
        PYRIGHT_EXIT=$?
        PYRIGHT_VER=$(pyright --version 2>/dev/null | head -1)
    else
        nix-shell --packages nodejs --run "npx --yes pyright@{{pyrightVersion}}" >"$PYRIGHT_LOG" 2>&1
        PYRIGHT_EXIT=$?
        PYRIGHT_VER="pyright@{{pyrightVersion}} (npx)"
    fi

    # ruff --output-format concise lines lack a severity word
    # (`path:l:c: ISC002 msg`), so count by finding-code shape; the
    # annotation tool regex covers mypy/pyright.
    N_RUFF=$(grep -Ec ':[0-9]+:[0-9]+: [A-Z]{1,4}[0-9]+ ' "$RUFF_LOG")
    N_MYPY=$($ANNOT "$MYPY_LOG" mypy 100000 2>/dev/null | wc -l)
    N_PYRIGHT=$($ANNOT "$PYRIGHT_LOG" pyright 100000 2>/dev/null | wc -l)

    {
        echo "# code inspect — \`${HASH}\`"
        echo
        echo "- commit: \`${HASH}\`  $(git log -1 --format=%cd --date=short)"
        echo "- target: \`{{target}}\`  |  ruff: \`$RUFF_VER\`  |  python(mypy): \`$("$PY" --version 2>/dev/null)\` | pyright: \`$PYRIGHT_VER\`"
        echo
        echo "| tool | exit | findings (error+warning) |"
        echo "|---|---|---|"
        echo "| ruff | $RUFF_EXIT | $N_RUFF |"
        echo "| mypy (advisory) | $MYPY_EXIT | $N_MYPY |"
        echo "| pyright (advisory) | $PYRIGHT_EXIT | $N_PYRIGHT |"
        echo
        echo "> ruff exit 0 = gate clean. mypy/pyright are advisory and not expected to be clean."
        echo
        for tool in ruff mypy pyright; do
            echo "## $tool"
            echo
            echo '```'
            head -n 120 "$TMP/${tool}.log" 2>/dev/null
            LINES=$(wc -l < "$TMP/${tool}.log" 2>/dev/null)
            if [ "${LINES:-0}" -gt 120 ]; then echo "... (${LINES} more lines truncated)"; fi
            echo '```'
            echo
        done
    } > "$OUT"

    echo "wrote $OUT"
    head -n 10 "$OUT"

    # Exit semantics:
    #   0  ruff gate clean (advisory findings don't affect the exit)
    #   1  ruff gate reported findings -> publish/CI-style callers should stop
    #   2  ruff could not run -> cannot verify, treat as failure
    if [ "$RUFF_EXIT" -eq 0 ]; then
        exit 0
    elif [ "$RUFF_EXIT" -eq -1 ]; then
        echo "STOP: ruff gate could not run - refusing to mark this tree clean" >&2
        exit 2
    else
        echo "STOP: ruff gate reported $N_RUFF finding(s); see $OUT" >&2
        exit 1
    fi

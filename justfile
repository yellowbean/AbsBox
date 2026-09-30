# List every available recipe with its documentation.
default:
    @just --list

# Run engine regression tests against: local (default), dev, or prod (Singapore servers).
#   just regression        -> local engine (http://localhost:8081)
#   just regression dev    -> remote Singapore dev server
#   just regression prod   -> production stable server in Singapore
regression engine="local":
    echo "Running regression tests against {{engine}} engine"
    ABSBOX_TEST_SERVER={{engine}} pytest absbox/tests/regression/test_main.py

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
publish env version:
    echo "Pushing to PyPI {{env}}"
    just regression dev
    just update-version {{version}}
    just tag {{env}} {{version}}
    just push-code




test: 
    echo "Running Tests"
    pytest absbox/tests/regression/test_main.py

# Bump the single source of truth. Sphinx docs derive their version from pyproject.toml.
update-version version:
    echo "Update Version: {{version}}"
    sed -i "s/^version = .*/version = \"{{version}}\"/g"  pyproject.toml
    uv lock

# Export marimo notebooks (docs/source/marimo/*.py) to static HTML.
export-marimo:
    uv run python docs/export_marimo.py

tag env version:
    echo "Tagging"
    git add pyproject.toml uv.lock
    git commit -m "bump version to-> < {{version}} >"
    git tag -a {{env}}{{version}} -m "{{env}}{{version}}"
    git push origin HEAD --tag

untag version:
    echo "Untagging"
    git tag -d {{version}}
    git push --delete origin

push-tag:
    echo "Pushing Tag"
    git push origin HEAD --tag

push-code:
    echo "Pushing Code"
    git push origin HEAD

live-doc:
    echo "Live Doc"
    sphinx-autobuild docs/source docs/build/html --open-browser --watch docs/source

publish env version:
    echo "Pushing to PyPI {{env}}"
    just test
    just update-version {{version}}
    just tag {{env}} {{version}}
    just push-code



test: 
    echo "Running Tests"
    pytest absbox/tests/regression/test_main.py

update-version version:
    echo "Update Version: {version}"
    # sed -i "s/^version = .*/version = \"{version}\"/g"  pyproject.toml   
    sed -i "s/^version = .*/version = {{version}}/g"  setup.cfg
    sed -i "s/^release = .*/release = \"{{version}}\"/g"   docs/source/conf.py
    sed -i "s/^version = .*/version = \"{{version}}\"/g"   docs/source/conf.py

tag version:
    echo "Tagging"
    git add pyproject.toml setup.cfg
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
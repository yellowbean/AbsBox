#bin/bash

rm dist/*

echo "<PUBLISH> Update Version"

sed -i"" -e "s/^release = .*/release = '$1'/g"  docs/source/conf.py
sed -i"" -e "s/^version = .*/version = '$1'/g"  docs/source/conf.py

sed -i"" -e "s/^version = .*/version = \"$1\"/g"  pyproject.toml
sed -i"" -e "s/^version = .*/version = $1/g"  setup.cfg

python3 -m build --wheel ;python3 -m twine upload --repository pypi dist/*  --verbose

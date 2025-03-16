#bin/bash

rm dist/*

echo "<PUBLISH> Update Version"
# version = '0.6.1',
# sed -i "s/version = .*/version = \'$2\',/g"  pyproject.toml

sed -i"" -e "s/^release = .*/release = '$1'/g"  docs/source/conf.py
sed -i"" -e "s/^version = .*/version = '$1'/g"  docs/source/conf.p

sed -i"" -e "s/^version = .*/version = \"$1\"/g"  pyproject.toml
sed -i"" -e "s/^version = .*/version = $1/g"  setup.cfg

python3 -m build --wheel ;python3 -m twine upload --repository testpypi dist/*  --verbose

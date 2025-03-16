#bin/bash

echo "ENV -> "$1
echo "Bump version to -> "$2
echo "Comment -> "$3

read -p "Is this a expected publish info (y/n)? " answer

if [ ${answer:0:1} != "y" ] ; then
  echo "Exiting "
  exit 1
fi

#echo "<PUBLISH> Running UT against PROD Engine"
#env TEST_RUN_SERVER="https://absbox.org/api/latest" pytest -k "test_translate"
pytest -k "test_translate"
if [ $? -ne 0 ]
then
  echo "<PUBLISH> Failing on UT:Translate"
  exit 2
fi
echo "Done with Translate"
#env TEST_RUN_SERVER="https://absbox.org/api/latest" pytest -k "test_resp"
pytest -k "test_resp"
if [ $? -ne 0 ]
then
  echo "<PUBLISH> Failing on UT:Running"
  exit 3
fi

pytest absbox/tests/regression/main.py
if [ $? -ne 0 ]
then
  echo "<PUBLISH> Failing on UT:Regression"
  exit 3
fi

echo "Done with Running"


# updating version on api version at Python packages
echo "<PUBLISH> Update Version"


sed -i "" -e "s/^version = .*/version = \"$2\"/g"  pyproject.toml
sed -i "" -e "s/^version = .*/version = $2/g"  setup.cfg


# update Python English Doc version
sed -i "" -e "s/^release = .*/release = \"$2\"/g"   docs/source/conf.py
sed -i "" -e "s/^version = .*/version = \"$2\"/g"   docs/source/conf.py



if [ $? -ne 0 ]
then
  echo "<PUBLISH> Failed to update version"
  exit 4
fi

# towncrier build --keep --yes --version $2
# 
# if [ $? -ne 0 ]
# then
#   echo "<PUBLISH> Failed to consolidate change log"
#   exit 5
# else 
#   echo "<PUBLISH> Consolidated change log"
#   mv changes/*.rst _history_changes/
# fi




echo "<PUBLISH> Tagging"
git add pyproject.toml setup.cfg
git commit -m "bump version to-> < $2 >"
git tag -a $1$2 -m "$3"
#
if [ $? -ne 0 ]
then
  echo "<PUBLISH> Failed to add Tag"
  exit 5
fi
#
echo "<PUBLISH> Pushing Tag"
git push origin HEAD --tag

if [ $? -ne 0 ]
then
  echo "<PUBLISH> Failed to push Tag"
  exit 6
fi

echo "<PUBLISH> Pushing "
git push origin HEAD

if [ $? -ne 0 ]
then
  echo "<PUBLISH> Failed to push"
  exit 7
fi


echo "<PUBLISH> Done ! "


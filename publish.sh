dir=$(dirname $0)

rm "$dir/dist/"* &> /dev/null

python -m pip install -r "$dir/devreqs.txt" > /dev/null
python setup.py sdist
python setup.py bdist_wheel
twine upload dist/*

echo "Add dist/*.tar.gz as a release on GitHub."

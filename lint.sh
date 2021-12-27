echo "Linting architrice:"
python -m black architrice
echo "Linting test:"
python -m black "test"
echo "Running tests:"
python -m unittest "test"

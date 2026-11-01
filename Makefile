.PHONY: build install devinstall preview publish clean format check test testcov

build: clean
	php README.md.php > README.md
	python3 -m build

install:
	python3 -m pip install .

devinstall:
	python3 -m pip install -e .[dev]

preview: build
	python3 -m twine upload -u __token__ --repository-url "https://test.pypi.org/legacy/" dist/*

publish: build
	python3 -m twine upload -u __token__ --repository-url "https://upload.pypi.org/legacy/" dist/*

clean:
	python3 -c "import shutil; shutil.rmtree('dist', ignore_errors=True)"
	python3 -c "import shutil; shutil.rmtree('build', ignore_errors=True)"
	python3 -c "import shutil; shutil.rmtree('flacopyus.egg-info', ignore_errors=True)"
	python3 -c "import shutil; shutil.rmtree('.ruff_cache', ignore_errors=True)"
	python3 -c "import shutil; shutil.rmtree('.pytest_cache', ignore_errors=True)"
	python3 -c "import shutil; shutil.rmtree('htmlcov', ignore_errors=True)"
	python3 -c "import os, os.path; os.remove('.coverage') if os.path.isfile('.coverage') else None"

format:
	python3 -m ruff format

check:
	-python3 -m ruff check
	-python3 -m pyright flacopyus tests

test:
	python3 -X dev -m pytest --doctest-modules

testcov:
	python3 -X dev -m coverage run --source=flacopyus --branch -m pytest --doctest-modules
	python3 -m coverage report -m
	python3 -m coverage html

.PHONY: build install devinstall preview publish clean format check

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
	python3 -c 'import shutil; shutil.rmtree("dist", ignore_errors=True)'
	python3 -c 'import shutil; shutil.rmtree("build", ignore_errors=True)'
	python3 -c 'import shutil; shutil.rmtree("flacopyus.egg-info", ignore_errors=True)'
	python3 -c 'import shutil; shutil.rmtree(".mypy_cache", ignore_errors=True)'
	python3 -c 'import shutil; shutil.rmtree(".ruff_cache", ignore_errors=True)'

format:
	python3 -m ruff format --line-length=200

check:
	-python3 -m ruff check
	-python3 -m mypy flacopyus

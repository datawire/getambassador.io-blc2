PRODUCT ?= generic
run: requirements.txt.stamp
	. ./venv/bin/activate && PYTHONUNBUFFERED=y ./$(PRODUCT)_blc.py '$(TARGET)'
.PHONY: run

lint: dev_requirements.txt.stamp
	. ./venv/bin/activate && MYPYPATH=$(CURDIR)/mypy-stubs mypy --exclude='^venv/.*' .
	. ./venv/bin/activate && flake8 .
.PHONY: lint

format: dev_requirements.txt.stamp
	. ./venv/bin/activate && isort $$(git ls-files ':*.py' ':*.pyi')
	. ./venv/bin/activate && black --line-length=93 --target-version=py36 --skip-string-normalization .
.PHONY: format

venv/bin/pip:
	python -m venv venv
%.txt.stamp: %.txt venv/bin/pip
	./venv/bin/pip install -r $<
	date > $@
dev_requirements.txt.stamp: requirements.txt.stamp

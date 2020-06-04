run: requirements.txt.stamp
	. ./venv/bin/activate && ./blc.py '$(TARGET)'
.PHONY: run

mypy: dev_requirements.txt.stamp
	. ./venv/bin/activate && MYPYPATH=$(CURDIR)/mypy-stubs mypy .
.PHONY: mypy

format: dev_requirements.txt.stamp
	. ./venv/bin/activate && isort $$(git ls-files ':*.py' ':*.pyi')
	. ./venv/bin/activate && black --line-length=93 --target-version=py36 --skip-string-normalization .
.PHONY: format

venv/bin/pip:
	virtualenv venv
%.txt.stamp: %.txt venv/bin/pip
	./venv/bin/pip install -r $<
	date > $@
dev_requirements.txt.stamp: requirements.txt.stamp

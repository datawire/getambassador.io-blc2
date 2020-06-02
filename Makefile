mypy: venv
	. ./venv/bin/activate && MYPYPATH=$(CURDIR)/mypy-stubs mypy .
.PHONY: mypy

venv/bin/pip:
	virtualenv venv
venv: venv/bin/pip requirements.txt
	./venv/bin/pip install -r requirements.txt
	touch $@

format: venv
	. ./venv/bin/activate && isort $$(git ls-files ':*.py' ':*.pyi')
	. ./venv/bin/activate && yapf -i $$(git ls-files ':*.py' ':*.pyi')
.PHONY: format

mypy: venv
	. ./venv/bin/activate && MYPYPATH=$(CURDIR)/mypy-stubs mypy .
.PHONY: mypy

venv/bin/pip:
	virtualenv venv
venv: venv/bin/pip requirements.txt
	./venv/bin/pip install -r requirements.txt
	touch $@

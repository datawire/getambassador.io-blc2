PRODUCT ?= generic
run: requirements.txt.stamp
	. ./venv/bin/activate && PYTHONUNBUFFERED=y ./$(PRODUCT)_blc.py '$(TARGET)'
.PHONY: run

# lint

lint: dev_requirements.txt.stamp package.json.dev.stamp
	. ./venv/bin/activate && MYPYPATH=$(CURDIR)/mypy-stubs mypy --exclude='^venv/.*' .
	. ./venv/bin/activate && flake8 .
	yarn run eslint .
.PHONY: lint

format: dev_requirements.txt.stamp package.json.dev.stamp
	. ./venv/bin/activate && isort $$(git ls-files ':*.py' ':*.pyi')
	. ./venv/bin/activate && black --line-length=93 --target-version=py36 --skip-string-normalization .
	yarn run eslint --fix .
.PHONY: format

# pip

venv/bin/pip:
	python3 -m venv venv
%.txt.stamp: %.txt venv/bin/pip
	./venv/bin/pip install -r $<
	date > $@
dev_requirements.txt.stamp: requirements.txt.stamp

# yarn

package.json.stamp: package.json yarn.lock
	yarn install --prod
	date > $@

package.json.dev.stamp: package.json yarn.lock
	yarn install
	date > $@

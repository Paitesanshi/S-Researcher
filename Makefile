PYTHON ?= python3.10
VENV ?= .venv

.PHONY: bootstrap install install-tuning check check-api-mock check-paper check-all smoke-cases help

bootstrap:
	PYTHON_BIN=$(PYTHON) ./scripts/bootstrap.sh

install:
	$(PYTHON) -m venv $(VENV)
	$(VENV)/bin/python -m pip install --upgrade pip
	$(VENV)/bin/python -m pip install -r requirements.txt
	$(VENV)/bin/python -m pip install --no-deps -e .

check:
	PYTHON_BIN=$(VENV)/bin/python ./researcher.sh --check

check-api-mock:
	$(VENV)/bin/python scripts/test_openai_compat.py

install-tuning:
	$(VENV)/bin/python -m pip install -r requirements-tuning.txt

check-paper:
	$(PYTHON) scripts/validate_submission.py

smoke-cases:
	PYTHON_BIN=$(VENV)/bin/python ./scripts/smoke_paper_cases.sh

check-all: check check-api-mock check-paper smoke-cases

help:
	./researcher.sh --help

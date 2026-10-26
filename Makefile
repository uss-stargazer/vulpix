VENV = .venv

ifeq ($(OS),Windows_NT)
	CLI = vulpix.exe
	PYTHON = python
	VENV_BIN = $(VENV)/Scripts
	VENV_ACT = $(VENV_BIN)/Activate.ps1
	ACT_CMD = powershell
else
	CLI = vulpix
	PYTHON = python3
	VENV_BIN = $(VENV)/bin
	VENV_ACT = $(VENV_BIN)/activate.sh
	ACT_CMD = source
endif

.PHONY: validate format lint dev clean build run

dev: $(VENV_BIN)/$(CLI) lint

$(VENV_BIN)/$(CLI): $(VENV_ACT)
	$(VENV_BIN)/pip install -e .

$(VENV_ACT): pyproject.toml
	$(PYTHON) -m venv $(VENV)
	$(ACT_CMD) $(VENV_ACT)

build: lint
	$(PYTHON) -m build

lint: format
	ruff check --fix

format: validate
	ruff format

validate:
	pyright

install:
	$(PYTHON) -m pip install -e .

install_deps:
	$(PYTHON) -m pip install --upgrade build pyright ruff

clean:
	$(PYTHON) -c "import pathlib, shutil, os; ps = [*pathlib.Path('.').rglob('__pycache__'), '.ruff_cache', 'dist', '.venv']; [shutil.rmtree(p) for p in ps if os.path.exists(p)]"

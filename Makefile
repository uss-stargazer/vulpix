VENV = .venv
CLI = vulpix

ifeq ($(OS),Windows_NT)
	VENV_BIN = $(VENV)/Scripts
	CLI_BIN = $(VENV_BIN)/$(CLI).exe
	PYTHON = python
else
	VENV_BIN = $(VENV)/bin
	CLI_BIN = $(VENV_BIN)/$(CLI)
	PYTHON = python3
endif

.PHONY: validate format lint all clean run

all: $(CLI_BIN) lint

$(CLI_BIN): pyproject.toml
	$(PYTHON) -m venv $(VENV)
	$(VENV_BIN)/pip install -e .

validate:
	pyright

format: validate
	ruff format

lint: format
	ruff check --fix

clean:
	$(PYTHON) -c "import pathlib, shutil; ps = [*pathlib.Path('.').rglob('__pycache__'), pathlib.Path('.ruff_cache')]; [shutil.rmtree(p) for p in ps if p.exists()]"

run: all
	./$(CLI_BIN)

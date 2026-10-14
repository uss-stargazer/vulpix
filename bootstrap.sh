#!/usr/bin/env bash

set -e

VULPIX_REPO="${VULPIX_REPO:-uss-stargazer/vulpix}"
VULPIX_BRANCH="${VULPIX_BRANCH:-main}"
VULPIX_REPO_GIT="https://github.com/$VULPIX_REPO"

command_exists() { command -v "$1" &>/dev/null; }
debug() { if [[ -v DEBUG ]]; then echo "DEBUG: $*" >&2; fi; }
info() { echo "INFO: $*" >&2; }
warn() { echo "WARN: $*" >&2; }
success() { echo "SUCCESS: $*" >&2; }
err() { echo "ERROR: $*" >&2; }
fatal() { echo "FATAL: $*" >&2 && exit 1; }
is_root() { [[ "$EUID" -eq 0 ]]; }
verify() {
  [[ $# -eq 1 ]]
  read -p "$1 (y/n): " -n 1 -r REPLY
  echo # new line
  case $REPLY in
    [yY]*) return 0 ;;
    *) return 1 ;;
  esac
}

info 'will install at highest privilege (run with root to install globally)'
is_root && level=system || level=user
verify "continue with bootstrap at $level level?" || fatal 'bootstrap aborted'

# IMPORTANT: Define standard dirs, which SHOULD BE THE SAME as defined in `src/vulpix/core/dirs.py`
is_root && {
  VULPIX_DATA='/var/lib/vulpix'
  VULPIX_CONFIG='/etc/vulpix'
} || {
  VULPIX_DATA="$HOME/.local/state/vulpix"
  VULPIX_CONFIG="$HOME/.config/vulpix"
}

# step 1: check python and git --------------------------------------------------------------------

command_exists python && PYTHON=python || PYTHON=python3

# for both python and git, it's the os package manager's domain to compile their binaries, so we
# simply check for their existence
command_exists $PYTHON || fatal 'python/python3 not available; install using os package manager'
command_exists git || fatal 'git not available; install using os package manager'

# step 2: install vulpix --------------------------------------------------------------------------

# this corresponds to the internal venv for the 'pip' package manager
# (see `src/vulpix/package_managers/pip.py`). this is necessary since some linux distros manually
# control the global pip env, so we need our own.
VENV="$VULPIX_DATA/pip/.venv"
info "bootstrapping venv in '$VENV'"
$PYTHON -m venv "$VENV"
[[ -f "$VENV/bin/pip" ]] || fatal "venv created but couldn't find pip binary!"

info "pip install vulpix"
"$VENV/bin/pip" uninstall --yes vulpix # make sure uninstalled so it actually updates it
"$VENV/bin/pip" install "git+$VULPIX_REPO_GIT@$VULPIX_BRANCH"
export PATH="$VENV/bin:$PATH" # temporary, but vulpix bootstraps itself to (using ensurevulpix) on first run
command_exists vulpix || fatal "install suppossedly succeeded, but vulpix isn't available"

# step 3: first run for registering blueprint packages --------------------------------------------

info "running vulpix for the first time"
vulpix sync

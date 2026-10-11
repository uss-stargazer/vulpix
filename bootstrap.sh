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
is_root() {
  [[ "$EUID" -eq 0 ]]
}
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

# TODO: workaround if pip doesn't allow global installs by default (like on debian)
$PYTHON -m pip install "git+$VULPIX_REPO_GIT@$VULPIX_BRANCH"
command_exists vulpix || fatal "install suppossedly succeeded, but vulpix isn't available"

# step 3: init blueprint --------------------------------------------------------------------------

BLUEPRINT="$VULPIX_CONFIG/blueprint.yaml"
default_blueprint=$(cat << 'EOF'
# vulpix blueprint for system/user

# specify target packages for system (by package manager)
packages:
  pip:
    - vulpix # updates vulpix itself automatically
  # ...other package managers

# specify target config for installed packages (controlled by each config manager)
configs:
  scripts: "Your config here!" # see `scripts` config manager docs for more info
  # ...other config managers

# misc settings (optional, see docs)
dotfiles: ~/.dotfiles # looks for dotfiles here
settings:
  threads: # auto     # number of task worker threads
  alt_screen: true    # fancy fullscreen for cli
EOF
)

if [[ ! -f "$VULPIX_CONFIG" ]] || verify "overwrite existing blueprint with default?"; then
  info 'setting up default blueprint'
  echo "$default_blueprint" >"$BLUEPRINT"
fi

# step 4: first run for registering blueprint packages --------------------------------------------

info 'running vulpix for the first time'
vulpix sync

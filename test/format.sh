#!/usr/bin/env bash
#
# Run yapf with system python3 for now
#
# Usage:
#   test/format.sh <function name>

install-pip() {
  # Debian Bookworm
  # Can't use this!  We get a new thing about "externally managed environment"
  sudo apt-get install python3-pip
}

install-venv() {
  sudo apt-get install python3.11-venv
}

readonly VENV=_tmp/yapf-venv

install-yapf() {
  if ! test -d $VENV; then
    python3 -m venv $VENV
  fi
  . $VENV/bin/activate
  python3 -m pip install yapf
}

yapf-files() {
  . $VENV/bin/activate
  python3 -m yapf -i "$@"
}

"$@"

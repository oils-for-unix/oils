#!/usr/bin/env bash
#
# Usage:
#   ./deps-py.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

dev-minimal() {
  # Python 2 packages for linting linting Python 2 code.
  pip install --user flake8 typing

  # Python 3 packages
  # - MyPy requires Python 3
  # - pexpect is for test/interactive.py
  pip3 install --user mypy pexpect
}

"$@"

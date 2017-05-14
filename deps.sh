#!/bin/bash
#
# Install development dependencies.
#
# Usage:
#   ./deps.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

install-ubuntu() {
  # python-dev: for pylibc
  # gawk: used by spec-runner.sh for the special match() function.
  # time: used to collect the exit code and timing of a test
  # libreadline-dev: needed for the build/prepare.sh Python build.
  sudo apt-get install python-dev gawk time libreadline-dev

  test/spec.sh install-shells
}

"$@"

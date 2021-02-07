#!/usr/bin/env bash
#
# Usage:
#   ./ninja.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

all() {
  mkdir --verbose -p _ninja/{bin,gen}
  ./configure.py
  ninja
}

clean() {
  rm --verbose -r -f _ninja
}

"$@"

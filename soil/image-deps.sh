#!/usr/bin/env bash
#
# Usage:
#   ./image-deps.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

dummy() {
  # gcc: time-helper is needed
  # git: for checking out code
  # python2: for various tools
  apt-get install -y gcc git python2
}

"$@"

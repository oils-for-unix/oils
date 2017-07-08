#!/usr/bin/env bash
#
# Usage:
#   ./build.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source common.sh

grammar() {
  opy_ pgen2 py27.grammar $GRAMMAR
}

"$@"

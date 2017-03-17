#!/bin/bash
#
# Run real shell code with osh and bash, and compare the results.
#
# Usage:
#   ./gold-test.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

_compare() {
  "$@" >_tmp/left.txt
  bin/osh "$@" >_tmp/right.txt
  diff -u _tmp/left.txt _tmp/right.txt
  echo PASS
}

# Uses
# - { busybox || true; } | head
# - $1
version-text() {
  _compare ./spec.sh version-text
}

count() {
  _compare ./count.sh all
  _compare ./count.sh parser
  _compare ./count.sh parser-port
  _compare ./count.sh runtime
}

"$@"

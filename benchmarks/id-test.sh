#!/usr/bin/env bash
#
# Usage:
#   benchmarks/id-test.sh <function name>

source benchmarks/id.sh
source test/common.sh

set -o nounset
set -o pipefail
set -o errexit

test-shell-prov() {
  shell-provenance-2 no-host 2022-12-29 _tmp/ \
    bin/osh
}

test-out-param() {
  local mylocal

  out-param mylocal
  assert "$mylocal" = 'returned'

  echo "mylocal=$mylocal"
}

soil-run() {
  run-test-funcs
}

"$@"

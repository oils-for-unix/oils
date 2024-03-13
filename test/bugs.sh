#!/usr/bin/env bash
#
# Junk drawer of repros for bugs
#
# Usage:
#   test/bugs.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

# bugs:
# echo | tr
# echo | cat
# history | less

esrch-code-1() {
  local n=$1
  for i in $(seq $n); do
    echo 'echo hi | tr a-z A-Z'
    #echo 'echo hi | cat'
  done
}

esrch-code-2() {
  local n=$1
  for i in $(seq $n); do
    echo 'history | less'
  done
}

esrch-test() {
  # I think

  local osh=bin/osh

  local osh=_bin/cxx-opt/osh
  ninja $osh

  esrch-code-1 1000 | $osh -i
}

"$@"

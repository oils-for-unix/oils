#!/usr/bin/env bash
#
# Usage:
#   benchamrks/builtin-io.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

readonly BIG=_tmp/1m_lines.txt

setup() {
  seq 1000000 > $BIG

}

# 25 ms
wc-big() {
  time wc -l $BIG
}

# bash takes 156 ms here!  Significantly slower than 'wc'.
# bin/osh in Python takes over 5 seconds!
#
# TODO:
# - Make sure bin/osh in C++ is reasonably fast.
# - Make sure a loop with read --line is reasonably fast.

mapfile-big() {
  time mapfile < $BIG
  echo ${#MAPFILE[@]}  # verify length
}


"$@"

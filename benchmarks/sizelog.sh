#!/bin/bash
#
# Usage:
#   benchmarks/sizelog.sh <function name>
#
# Example:
#   $ build/mycpp.sh compile-osh-parse-sizelog
#   $ benchmarks/sizelog.sh alloc-hist

set -o nounset
set -o pipefail
set -o errexit

source benchmarks/common.sh

alloc-hist() {
  local prog=${1:-configure}
  _bin/osh_parse.sizelog $prog | egrep '^new|^malloc' | hist
}

list-lengths() {
  ### Show the address of each list, its length, and its maximum element
  local prog=${1:-configure}
  _bin/osh_parse.sizelog $prog | egrep '^0x' | benchmarks/sizelog.py
}

# Hm this shows that almost all lists have 1-3 elements.
# Are these the spid lists?
#
# Should we then do small size optimization?
# TODO: Where are they allocated from?  Can uftrace answer that?
#
#   count listlength
#     734 6
#    1835 5
#   10718 4
#   66861 2
#   67841 3
#  179893 1
#
# 329628 _tmp/lists.txt


length-hist() {
  list-lengths "$@" | awk '{print $2}' > _tmp/lists.txt
  cat _tmp/lists.txt | hist
  wc -l _tmp/lists.txt
}

"$@"

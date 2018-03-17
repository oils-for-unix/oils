#!/bin/bash
#
# 2018 experiments on determism.  There are 2017 experiments in compare.sh and
# misc/determinism.py.
#
# I think I fixed the misc.Set() bug in OPy, but there still remained CPython
# determinism.  However I haven't reproduced it on a small case.
#
# Usage:
#   ./determinism.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

dictset() {
  local n=${1:-30}
  local python=${2:-python}

  seq $n | $python -c '
import sys
d = {}
s = set()
for line in sys.stdin:
  i = line.strip()
  d[i] = 1
  s.add(i)
print "D", " ".join(d.keys())
print "S", " ".join(s)
'
}

# Each iteration is stable.
compare-iters() {
  for i in $(seq 10); do
    # Run it twice with the same seed
    dictset
  done
}

# Changing the seed changes the order.
compare-seed() {
  for seed in 1 2 3; do
    echo "seed = $seed"
    # Run it twice with the same seed
    PYTHONHASHSEED=$seed $0 dictset
    PYTHONHASHSEED=$seed $0 dictset
  done
}

# Hm this is stable oto.
compare-python() {
  for i in $(seq 10); do
    dictset
    dictset '' ../_devbuild/cpython-full/python
  done
}

#
# OPy
#

# See smoke.sh

"$@"

#!/usr/bin/env bash
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

# Trying to reproduce problem with pyassem.py and Block() in order_blocks, but
# this does NOT do it.
# I had to add sorted() to make it stable there, but here I do not?  Why?

# See also: https://github.com/NixOS/nixpkgs/issues/22570
#
# "No, the sets are built as real sets and then marshalled to .pyc files in a
# separate step. So on CPython an essentially random order will end up in the
# .pyc file. Even CPython 3.6 gives a deterministic order to dictionaries but
# not sets. You could ensure sets are marshalled in a known order by changing
# the marshalling code, e.g. to emit them in sorted order (on Python 2.x; on
# 3.x it is more messy because different types are more often non-comparable)."
#
# Is that accurate?  The issue here is not sets as marshalled constants; it's
# USING sets in the compiler.
#
# set([1, 2, 3]) and {'a': 'b'} do not produce literal constants!

dictset() {
  local n=${1:-30}
  local python=${2:-python}

  seq $n | $python -c '
import sys
class Block:
  def __init__(self, x):
    self.x = x
  def __repr__(self):
    return str(self.x)

s = set()
hashes = []
for line in sys.stdin:
  b = Block(line.strip())
  hashes.append(hash(b))
  s.add(b)
print s
print hashes
'
}

dictset2() {
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

# Aha!  hash(Block()) is still not deterministic with a fixed seed, because it
# uses the address?
#
# https://stackoverflow.com/questions/11324271/what-is-the-default-hash-in-python

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

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

# Hm this isn't that fast either, about 100 ms.
python-big() {
  time python -S -c '
import sys
i = 0
for line in sys.stdin:
  i += 1
print(i)
' < $BIG
}

bash-syscall() {
  # Shows that there are tons of read(0, 1) calls!
  seq 20 | strace -e read -- bash -c 'mapfile'
}

python-syscall() {
  # Does read(0, 4096).  A saner way to read files
  seq 20 | strace -e read -- python -c '
import sys
for line in sys.stdin:
  print(line)
'
}


"$@"

#!/usr/bin/env bash
#
# Benchmarks for YSH for loop
#
# Usage:
#   benchmarks/ysh-for.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

YSH=_bin/cxx-opt/ysh
OSH=_bin/cxx-opt/osh

sum() {
  echo "    YSH for loop"

  time $YSH -c '
  var sum = 0
  for i in (0 .. $1) {
    setvar sum += i
  }
  echo "i = $i"
  echo "sum = $sum"
  ' dummy "$@"
}

sum-closures() {
  echo "    YSH closures"

  time $YSH -c '
  var sum = 0
  for __hack__ in (0 .. $1) {  # trigger allocation
    setvar sum += __hack__
  }
  # Does not leak!
  #echo "__hack__ = $__hack__"
  echo "sum = $sum"
  ' dummy "$@"
}

sum-py() {
  echo '    PY'
  time python3 -c '
import sys
n = int(sys.argv[1])
sum = 0
for i in range(n):
  sum += i
print(f"sum = {sum}")
  ' "$@"
}

sum-sh() {
  local sh=$1
  local n=$2

  echo "    $sh"
  time $sh -c '
n=$1
sum=0
i=0
while test $i -lt $n; do
  sum=$(( sum + i ))
  i=$(( i + 1 ))
done
echo "sum = $sum"
  ' "$@"
}

compare() {
  local n=${1:-1000000}
  local OILS_GC_STATS=${2:-}

  ninja $OSH $YSH

  sum-py $n
  echo

  export OILS_GC_STATS
  sum $n
  echo

  sum-closures $n
  echo

  if true; then
    # 3.9 seconds
    sum-sh bash $n
    echo

    # 3.7 seconds
    sum-sh $OSH $n
    echo

    # 1.2 seconds
    sum-sh dash $n
    echo

    # 2.3 seconds
    sum-sh zsh $n
    echo

    # 3.1 seconds
    sum-sh mksh $n
    echo
  fi
}

"$@"

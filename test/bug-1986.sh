#!/usr/bin/env bash
#
# Potentially Long-running stress tests
#
# Usage:
#   test/stress.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

# GC bug?

replace-ysh() {
  #local ysh=_bin/cxx-opt/ysh
  local ysh=_bin/cxx-dbg/ysh
  #local ysh=_bin/cxx-asan/ysh
  ninja $ysh

  # gc_mylib.cc sets threshold to 50K
  # it doesn't seem to matter!
  #
  # Oh does this have to do with recursively calling back into the interpreter?

  #GDB='gdb --args '
  GDB=''

  # Stats show that there are 29 collections
  OILS_GC_STATS=1 OILS_GC_VERBOSE=1 OILS_GC_THRESHOLD=10 $GDB $ysh -c '
env | grep OILS

var x = "z"
var r = "replace"

for i in (1 .. 2000) { 
  #echo $i

  # creates exponentially sized strings!
  # TODO: document string size limits
  #setvar x = x=>replace("z", "zz")

  # Works fine
  #setvar x = x=>replace("z", "y")

  # Hm does not crash?
  setvar x = x=>replace("z", ^"hi $r")
}
echo $x
'
}

shvar-replace() {
  ### failing test from Julian

  #local ysh=_bin/cxx-asan+gcalways/ysh
  local ysh=_bin/cxx-dbg/ysh
  #local ysh=_bin/cxx-asan/ysh
  ninja $ysh
  #GDB='gdb --args'
  GDB=''

  # Takes a few tries, even with OILS_GC_THRESHOLD

  local i=0
  while true; do
    echo "=== try $i"

    OILS_GC_STATS=1 OILS_GC_VERBOSE=1 OILS_GC_THRESHOLD=10 $GDB $ysh -c '
shvar FOO=bar {
  for x in (1 .. 500) {
    var Q = "hello"
    setvar Q = Q=>replace("hello","world")
  }
}
echo $Q
'
    i=$(( i + 1 ))
  done
}

replace-exp() {
  local osh=_bin/cxx-opt/osh
  ninja $osh

  # 2.791 seconds for 19 iterations, up to 1 MB
  SH=$osh

  SH=bash
  for sh in bash $osh; do
    echo "=== $sh ==="
    echo

    time $sh -c '
x=z
for i in {1..19}; do
  x=${x//z/zz}
  echo len=${#x}
done
  '
  done
}

# Reduce this bug
# https://github.com/oilshell/oil/issues/1986

bug-1986() {
  local ysh=_bin/cxx-dbg/ysh
  #local ysh=_bin/cxx-asan/ysh
  ninja $ysh

  local prefix
  #prefix=''
  #prefix="$PWD/$ysh -x"
  prefix="gdb --args $PWD/$ysh"

  cd bug/code

  set -x
  $prefix src/amd-scripts/amd-test --select imperfect aomp-amd-staging.cfg 14
}

"$@"

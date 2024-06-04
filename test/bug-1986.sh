#!/usr/bin/env bash
#
# Potentially Long-running stress tests
#
# Usage:
#   test/stress.sh <function name>

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

  OIL_GC_STATS=1 OILS_GC_VERBOSE=1 OILS_GC_THRESHOLD=100 $GDB $ysh -c '
var x = "z"
for i in (1 .. 1000) { 
  echo $i
  # z -> zz creates exponential data
  setvar x = x=>replace("z", "y")
  setvar x = x=>replace("y", "z")
}
echo $x
'
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

  GDB="gdb --args $PWD/$ysh"
  cd bug/code

  set -x
  $GDB src/amd-scripts/amd-test --select imperfect aomp-amd-staging.cfg 14
}

"$@"

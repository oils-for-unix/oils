#!/usr/bin/env bash
#
# Usage:
#   benchmarks/gc.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source devtools/common.sh  # banner

compare() {
  local file=${1:-benchmarks/testdata/configure-coreutils}


  # ~50ms
  banner dash
  time dash -n $file
  echo

  # 91 ms
  echo bash
  time bash -n $file
  echo

  # TODO:
  # - mutator only: bumpleak

  # ~174 ms
  banner 'mallocleak'
  local bin=_bin/cxx-mallocleak/osh_eval
  ninja $bin
  time $bin --ast-format none -n $file
  echo

  # ~204 ms -- this is slower than mallocleak!  But all we're doing is checking
  # collection policy, and updating GC stats.  Hm.
  banner 'opt'

  # ~308 ms
  # Garbage-collected Oil binary
  # TODO: OIL_GC_ON_EXIT is disabled
  local bin=_bin/cxx-opt/osh_eval
  ninja $bin
  time $bin --ast-format none -n $file

  # TODO: OIL_GC_ON_EXIT=1
  # I think you want 
  # - gHeap.LazyProcessExit("OIL_GC_ON_EXIT")  -- for Oil
  # - gHeap.CleanProcessExit("OIL_GC_ON_EXIT")  -- for benchmarks

  # TODO: OIL_GC_THRESHOLD=low -- measure traceing and collection

  # tcmalloc?

  # ~330 ms -- free() is slow
  banner 'opt with free'
  time OIL_GC_ON_EXIT=1 $bin --ast-format none -n $file
}

"$@"

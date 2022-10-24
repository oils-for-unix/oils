#!/usr/bin/env bash
#
# Usage:
#   benchmarks/gc.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source devtools/common.sh  # banner

# TODO:
# - -m32 speed comparison would be interesting, see mycpp/demo.sh
# - also it's generally good for testing

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

  # ~174 ms
  banner 'bumpleak'
  local bin=_bin/cxx-bumpleak/osh_eval
  ninja $bin
  time $bin --ast-format none -n $file
  echo

  # ~174 ms
  banner 'mallocleak'
  local bin=_bin/cxx-mallocleak/osh_eval
  ninja $bin
  time $bin --ast-format none -n $file
  echo

  # ~204 ms -- this is slower than mallocleak!  But all we're doing is checking
  # collection policy, and updating GC stats.  Hm.
  banner 'OPT with high threshold - malloc only'

  # ~308 ms
  # Garbage-collected Oil binary
  # TODO: OIL_GC_ON_EXIT is disabled
  local bin=_bin/cxx-opt/osh_eval
  ninja $bin
  time $bin --ast-format none -n $file

  # tcmalloc?

  # ~330 ms -- free() is slow
  banner 'OPT with high threshold - malloc + free'
  time OIL_GC_ON_EXIT=1 $bin --ast-format none -n $file

  echo 'TODO'
  if false; then
    banner 'OPT with low threshold - malloc + free + mark/sweep'

    # TODO: crashes!
    time OIL_GC_THRESHOLD=1000 OIL_GC_ON_EXIT=1 $bin --ast-format none -n $file
  fi
}

"$@"

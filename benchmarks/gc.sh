#!/usr/bin/env bash
#
# Usage:
#   benchmarks/gc.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

# See benchmarks/gperftools.sh.  I think the Ubuntu package is very old

download-tcmalloc() {
  # TODO: move this to ../oil_DEPS ?
  wget --directory _deps \
    https://github.com/gperftools/gperftools/releases/download/gperftools-2.10/gperftools-2.10.tar.gz

  # Then ./configure; make; sudo make install
  # installs in /usr/local/lib

  # Note: there's a warning about libunwind -- maybe install that first.  Does
  # it only apply to CPU profiles?
}

debug-tcmalloc() {
  touch mycpp/marksweep_heap.cc

  # No evidence of difference
  for bin in _bin/cxx-{mallocleak,tcmallocleak}/osh_eval; do
    echo $bin
    ninja $bin

    ldd $bin
    echo

    ls -l $bin
    echo

    # Still linking against glibc
    nm $bin | egrep -i 'malloc|calloc'
    #wc -l
    echo
  done
}

banner() {
  echo -----
  echo "$@"
}

run-osh() {
  local bin=$1
  ninja $bin
  time $bin --ast-format none -n $file
}

# TODO:
# - -m32 speed comparison would be interesting, see mycpp/demo.sh
# - also it's generally good for testing

compare() {
  local file=${1:-benchmarks/testdata/configure-coreutils}

  # ~50ms
  banner 'dash'
  time dash -n $file
  echo

  # 91 ms
  banner 'bash'
  time bash -n $file
  echo

  # ~88 ms!  But we are using more system time than bash/dash -- is it
  # line-based I/O?
  banner 'bumpleak'
  local bin=_bin/cxx-bumpleak/osh_eval
  run-osh $bin

  # Not much faster
  banner 'tcmallocleak'
  local tcmalloc_bin=_bin/cxx-tcmallocleak/osh_eval
  run-osh $tcmalloc_bin

  # ~174 ms
  banner 'mallocleak'
  local bin=_bin/cxx-mallocleak/osh_eval
  run-osh $bin

  # ~204 ms -- this is slower than mallocleak!  But all we're doing is checking
  # collection policy, and updating GC stats.  Hm.
  banner 'OPT with high threshold - malloc only'

  # ~308 ms
  # Garbage-collected Oil binary
  local bin=_bin/cxx-opt/osh_eval
  run-osh $bin

  # ~330 ms -- free() is slow
  banner 'OPT with high threshold - malloc + free'
  OIL_GC_ON_EXIT=1 run-osh $bin

  # WOW: 192 ms!  It doesn't have the huge free() penalty that glibc does.
  # Maybe it doesn't do all the malloc_consolidate() stuff.
  banner 'OPT with high threshold - tcmalloc + free'
  OIL_GC_ON_EXIT=1 run-osh $tcmalloc_bin

  echo 'TODO'
  if false; then
    banner 'OPT with low threshold - malloc + free + mark/sweep'

    # TODO: crashes!
    OIL_GC_THRESHOLD=1000 OIL_GC_ON_EXIT=1 run-osh $bin
  fi
}

"$@"

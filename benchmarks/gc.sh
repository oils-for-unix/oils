#!/usr/bin/env bash
#
# Usage:
#   benchmarks/gc.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)

source test/tsv-lib.sh

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
  for bin in _bin/cxx-{opt,tcmalloc}/osh_eval; do
    echo $bin
    ninja $bin

    ldd $bin
    echo

    ls -l $bin
    echo

    # Check what we're linking against
    nm $bin | egrep -i 'malloc|calloc'
    #wc -l
    echo
  done
}

install-m32() {
  # needed to compile with -m32
  sudo apt install gcc-multilib g++-multilib
}

max-rss() {
  # %e is real time
  /usr/bin/time --format '%e %M' -- "$@"
}

compare-m32() {
  for bin in _bin/cxx-opt{,32}/osh_eval.stripped; do
    echo $bin
    ninja $bin

    ldd $bin
    echo

    file $bin
    echo

    ls -l $bin
    echo

    # 141136 KiB vs. 110924 KiB.  Significant savings, but it's slower.
    max-rss $bin --ast-format none -n benchmarks/testdata/configure-coreutils

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
# - integrate with benchmarks/gperftools.sh, and measure memory usage
# - Use time-tsv, and max_rss stat, like %M

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

  # 274 ms
  banner 'zsh'
  time zsh -n $file
  echo

  # ~88 ms!  But we are using more system time than bash/dash -- it's almost
  # certainly UNBUFFERED line-based I/O!
  banner 'bumpleak'
  local bin=_bin/cxx-bumpleak/osh_eval
  OIL_GC_STATS=1 run-osh $bin

  # 165 ms
  banner 'mallocleak'
  local bin=_bin/cxx-mallocleak/osh_eval
  run-osh $bin

  # 184 ms
  # Garbage-collected Oil binary
  banner 'OPT - malloc only'
  local bin=_bin/cxx-opt/osh_eval
  run-osh $bin

  # 277 ms -- free() is slow
  banner 'OPT GC on exit - malloc + free'
  OIL_GC_STATS=1 OIL_GC_ON_EXIT=1 run-osh $bin

  # Surprisingly, -m32 is SLOWER, even though it allocates less.
  # My guess is because less work is going into maintaining this code path in
  # GCC.

  # 223 ms
  # 61.9 MB bytes allocated
  banner 'OPT32 - malloc only'
  local bin=_bin/cxx-opt32/osh_eval
  run-osh $bin

  # 280 ms
  banner 'OPT32 GC on exit - malloc + free'
  OIL_GC_STATS=1 OIL_GC_ON_EXIT=1 run-osh $bin

  # 184 ms
  banner 'tcmalloc - malloc only'
  local tcmalloc_bin=_bin/cxx-tcmalloc/osh_eval
  run-osh $tcmalloc_bin

  # Faster: 218 ms!  It doesn't have the huge free() penalty that glibc does.
  # Maybe it doesn't do all the malloc_consolidate() stuff.
  banner 'tcmalloc GC on exit - malloc + free'
  OIL_GC_ON_EXIT=1 run-osh $tcmalloc_bin

  echo 'TODO'
  if false; then
    banner 'OPT with low threshold - malloc + free + mark/sweep'

    # TODO: crashes!
    OIL_GC_THRESHOLD=1000 OIL_GC_ON_EXIT=1 run-osh $bin
  fi
}

compare-two-files() {
  compare

  # Similar, smaller file.  zsh is faster
  compare benchmarks/testdata/configure

  #compare testdata/completion/git-completion.bash
  #compare testdata/osh-runtime/abuild
}

"$@"

#!/usr/bin/env bash
#
# Usage:
#   benchmarks/sizelog.sh <function name>
#
# Example:
#   ninja _ninja/osh_eval.alloclog
#   benchmarks/alloclog.sh alloc-hist

set -o nounset
set -o pipefail
set -o errexit

source benchmarks/common.sh

# ~191K total allocations for configure
# ~2.1M for abuild
# ~15.7M for benchmarks/testdata/configure
# ~42.8M for benchmarks/testdata/configure-coreutils
alloc-hist() {
  local prog=${1:-configure}
  _bin/osh_eval.alloclog -n $prog | egrep '^new|^malloc' | hist
  #_bin/osh_eval.sizelog -n $prog | egrep '^new|^malloc' | hist
}

list-lengths() {
  ### Show the address of each list, its length, and its maximum element
  local prog=${1:-configure}
  _bin/osh_eval.alloclog -n $prog | egrep '^0x' | benchmarks/alloclog.py
}

# Hm this shows that almost all lists have 1-3 elements.
# Are these the spid lists?
#
# Should we then do small size optimization?
# TODO: Where are they allocated from?  Can uftrace answer that?
#
#   count listlength
#     734 6
#    1835 5
#   10718 4
#   66861 2
#   67841 3
#  179893 1
#
# 329628 _tmp/lists.txt


length-hist() {
  list-lengths "$@" | awk '{print $2}' > _tmp/lists.txt
  cat _tmp/lists.txt | hist
  wc -l _tmp/lists.txt
}

build-variants() {
  build/native_graph.py

  # opt uses dumb_alloc
  # TODO: might want _bin/osh_eval.tcmalloc, which depends on a system library
  ninja _bin/osh_eval.{opt,malloc}
}

time-mem() {
  local out=$1
  local prefix=$2
  shift 2
  /usr/bin/time -o $out --append --format "$prefix\\t%U\\t%M" -- "$@" >/dev/null
}

measure() {
  local out=_tmp/alloclog.tsv

  rm -f $out

  for variant in .opt .malloc .tcmalloc; do
    echo $variant
    #time-mem _bin/osh_eval$variant -c 'echo hi'

    # dumb_alloc: 3876 KiB, GNU: 4088, tcmalloc: 9200.
    # OK that's actually not too bad for GNU.  Not too much overhead.
    #local file=configure

    # dumb_alloc: 77460, GNU: 93976, tcmalloc: 70732
    # Gah that is not good.  I want to get these numbers down.
    local file=benchmarks/testdata/configure-coreutils

    time-mem $out "$variant\\tparse" _bin/osh_eval$variant --ast-format none -n $file

    time-mem $out "$variant\\trun" _bin/osh_eval$variant benchmarks/compute/fib.sh 1000 44
  done

  cat $out
}

"$@"

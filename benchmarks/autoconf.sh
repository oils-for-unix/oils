#!/usr/bin/env bash
#
# Why is CPython configure slower under OSH?
#
# Usage:
#   benchmarks/autoconf.sh <function name>
#
# Examples:
#   $0 measure-alloc-overhead
#   $0 measure-syscalls

set -o nounset
set -o pipefail
set -o errexit

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)

source benchmarks/cachegrind.sh  # with-cachegrind
source benchmarks/callgrind.sh  # with-cachegrind
source test/tsv-lib.sh  # $TAB

readonly BASE_DIR=_tmp/autoconf
readonly PY_CONF=$REPO_ROOT/Python-2.7.13/configure

#
# Trying to measure allocation/GC overhead 
#
# This doesn't help because bumpleak/bumproot are **slower** on bigger heaps.
# There's less cache locality!
#

cpython-configure-tasks() {
  local -a variants=( opt+bumpleak opt+bumproot opt )
  for v in ${variants[@]}; do
    echo "${v}${TAB}_bin/cxx-$v/osh"
  done
}

cpython-setup() {
  cpython-configure-tasks | while read -r _ osh; do
    ninja $osh
  done
}

measure-alloc-overhead() {
  local base_dir=$REPO_ROOT/$BASE_DIR/cpython-configure
  rm -r -f -v $base_dir

  cpython-configure-tasks | while read -r variant osh; do
    osh=$REPO_ROOT/$osh

    local task_dir=$base_dir/$variant

    mkdir -p $task_dir
    pushd $task_dir > /dev/null

    local -a flags=(
        --output "$base_dir/$variant.tsv" 
        --rusage
    )

    local -a time_argv

    time_argv=(
      time-tsv --print-header
      "${flags[@]}"
      --field variant
    )
    "${time_argv[@]}"

    time_argv=(
      time-tsv --append
      "${flags[@]}"
      --field "$variant"
      -- $osh $PY_CONF
    )

    #echo "${time_argv[@]}"
    "${time_argv[@]}"

    popd > /dev/null

  done
}

#
# Now try strace
#

strace-tasks() {
  echo "bash${TAB}bash"
  echo "dash${TAB}dash"
  echo "osh${TAB}$REPO_ROOT/_bin/cxx-opt/osh"
}

measure-syscalls() {
  local base_dir=$REPO_ROOT/_tmp/strace
  strace-tasks | while read -r sh_label sh_path; do
    local dir=$base_dir/$sh_label
    mkdir -p $dir

    local counts=$base_dir/$sh_label.txt

    pushd $dir
    strace -o $counts -c $sh_path $PY_CONF
    popd
  done
}

#
# Cachegrind
#

measure-valgrind() {
  local tool=$1

  # opt seems to give OK results, but I thought dbg was more accurate
  #local osh=_bin/cxx-opt/osh
  local osh=_bin/cxx-dbg/osh

  ninja $osh

  local osh=$REPO_ROOT/$osh

  local base_dir=$REPO_ROOT/_tmp/$tool

  local dir=$base_dir/cpython-configure
  rm -r -f -v $dir

  local out_file=$base_dir/cpython-configure.txt

  mkdir -v -p $dir

  pushd $dir
  $tool $out_file $osh $PY_CONF
  popd
}

measure-cachegrind() {
  measure-valgrind with-cachegrind
}

measure-callgrind() {
  # This takes ~5 minutes with opt binary, ~6:43 with dbg
  # vs ~15 seconds uninstrumented
  time measure-valgrind with-callgrind
}

# Note:
# benchmarks/osh-runtime.sh compares our release, which does not have #ifdef
# GC_TIMING, so we don't know total GC time.

# TODO:
#
# - Run locally, reproduce GC_TIMING - this is not in the release build
#   - it seems to say only 143 ms total GC time, but we're seeing 1.5+ seconds
#   slowdown on Cpython configure vs. bash
#   - I want a local run that automates it, and returns PERCENTAGES for elapsed
#   time, sys time, user time
# - We also might not want to amortize free() inside Allocate()
#   - #ifdef LAZY_FREE I think!  That might show a big slowdown with free

patch-pyconf() {
  # temporary
  echo 'times > $SH_BENCHMARK_TIMES' >> $PY_CONF
}

measure-elapsed() {
  local osh=_bin/cxx-opt/osh
  ninja $osh

  local base_dir=$REPO_ROOT/_tmp/elapsed

  strace-tasks | while read -r sh_label sh_path; do
    #case $sh_label in bash|dash) continue ;; esac

    local dir=$base_dir/$sh_label
    mkdir -p $dir

    pushd $dir

    local -a flags=(
        --output "$base_dir/$sh_label.tsv" 
        --rusage
    )

    local -a time_argv

    time_argv=(
      time-tsv --print-header
      "${flags[@]}"
      --field sh_label
    )
    "${time_argv[@]}"

    time_argv=(
      time-tsv --append
      "${flags[@]}"
      --field "$sh_label"
      -- $sh_path $PY_CONF
    )

    #echo "${time_argv[@]}"

    _OILS_GC_VERBOSE=1 OILS_GC_STATS_FD=99 \
      SH_BENCHMARK_TIMES=$base_dir/$sh_label.times.txt \
      "${time_argv[@]}" \
      99>$base_dir/$sh_label.gc-stats.txt

    local counts=$base_dir/$sh_label.txt

    popd
  done
}

### Why is clone() taking longer according to strace?

fork-tasks() {
  echo "bash${TAB}bash"
  echo "dash${TAB}dash"

  # Hm this is noisy, but cxx-opt-sh does seem slower
  echo "osh${TAB}$REPO_ROOT/_bin/cxx-opt/osh"
  echo "osh${TAB}$REPO_ROOT/_bin/cxx-opt-sh/osh"
}

measure-fork() {
  fork-tasks | while read -r sh_label sh_path; do
    #case $sh_label in bash|dash) continue ;; esac

    echo "=== $sh_path ==="

    # Builtin is very fast
    #time $sh_path -c 'for i in $(seq 100); do true; done'

    # Hm this is very noisy
    # TODO use hyperfine?
    time $sh_path -c 'for i in $(seq 100); do /bin/true; done'

    case $sh_label in
      osh)
        # Oops, we are not symlinking to the .stripped binary!
        # This is explicitly done for symbols and benchmarking.
        # Hm does that make it slower then?

        ls -l -L $sh_path
        ldd $sh_path
        ;;
    esac
  done
}

# $ head _tmp/elapsed/*.times.txt
# ==> _tmp/elapsed/bash.times.txt <==
# 0m0.213s 0m0.477s
# 0m8.233s 0m2.931s
# 
# ==> _tmp/elapsed/dash.times.txt <==
# 0m0.217s 0m0.463s
# 0m8.281s 0m2.922s
# 
# ==> _tmp/elapsed/osh.times.txt <==
# 0m0.360s 0m0.720s
# 0m8.790s 0m2.960s

# shell user time - GC and allocs
# shell system time - ???
# child user time - ???
#   TODO: count how many processes this is.  
#   It's more than 500 ms
#   Is that 500 processes, and 1 ms per process?

"$@"

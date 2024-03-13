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
# Trying to measure allocation/GC overhead -- kinda failed because bumproot is
# **slower** on bigger heaps.  There's less cache locality!
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

"$@"

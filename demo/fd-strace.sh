#!/usr/bin/env bash
#
# Usage:
#   ./fd-strace.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

lines-to-remove() {
  local sh=$1
  case $sh in
    dash) echo 5 ;;
    */ash) echo 0 ;;
    */osh) echo 24 ;;
    *) echo 0 ;;
  esac
}

readonly BASE_DIR=_tmp/fd-strace

do-strace() {
  local sh=$1
  local fd=$2

  local num_lines
  num_lines=$(lines-to-remove $sh)

  local fil
  num_lines=$(lines-to-remove $sh)

  echo ===
  echo $sh
  echo

  local out
  out=$BASE_DIR/$fd-$(basename $sh).txt

  # PR adds lseek
  strace \
    -e open,openat,fcntl,dup2,close,lseek \
    $sh demo/fd-number.sh $fd  2>&1 |
    tail -n +$num_lines | tee $out
  }

compare() {
  mkdir -p $BASE_DIR
  rm -f -v $BASE_DIR/*

  local osh=_bin/cxx-dbg/osh

  ninja $osh

  # dash can only handle descriptor 8
  for sh in dash _tmp/shells/ash $osh; do
    do-strace $sh 8
  done

  for sh in _tmp/shells/ash $osh; do
    for fd in 10 12; do
      do-strace $sh $fd
    done
  done

  wc -l $BASE_DIR/*
}

side-by-side() {
  # trick from Claude

  printf '%-30s ---  %s\n' $1 $2
  pr --merge --omit-header $1 $2
  #pr $1 $2
}

osh-ash() {
  local fd=${1:-8}
  side-by-side $BASE_DIR/$fd-{osh,ash}.txt
}

osh-dash() {
  local fd=${1:-8}
  side-by-side $BASE_DIR/$fd-{osh,dash}.txt
}

"$@"

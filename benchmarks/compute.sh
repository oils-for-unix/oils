#!/bin/bash
#
# Usage:
#   benchmarks/compute.sh <function name>
#
# TODO:
# - awk versions of fib, word_freq
# - assert that stdout is identical

set -o nounset
set -o pipefail
set -o errexit

readonly OSH_CC=_bin/osh_eval.opt.stripped

fib-demo() {
  local iters=200

  echo --- python
  time benchmarks/compute/fib.py $iters 44 | wc -l

  for sh in dash bash $OSH_CC; do

    echo --- $sh
    time $sh benchmarks/compute/fib.sh $iters 44 | wc -l
  done

}

word-freq-demo() {
  #local in=README.md  # breaks on the * characters!
  local in=configure  # still doesn't work because of / and \ chars

  local out=_tmp/compute
  mkdir -p $out

  echo --- python
  time benchmarks/compute/word_freq.py 100 < $in | sort -n > $out/py.txt

  # TODO: bash isn't correct!
  for sh in $OSH_CC; do
  #for sh in bash; do
    # 2 seconds
    echo --- $sh
    time $sh benchmarks/compute/word_freq.sh 100 < $in | sort -n > $out/$(basename $sh).txt
  done

  md5sum $out/*
}


"$@"

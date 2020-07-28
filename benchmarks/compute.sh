#!/bin/bash
#
# Usage:
#   benchmarks/compute.sh <function name>
#
# List of benchmarks:
#
# - fib: integer, loop, assignment (shells don't have real integers
# - word_freq: hash table / assoc array (OSH uses a vector<pair<>> now!)
#              also integer counter
# - bubble sort: indexed array (bash uses a linked list?)
#                todo: string and integer
# - palindrome: string, slicing, unicode
#
# Also:
# - benchmarks/parse-help: realistic string processing
#
# TODO:
# - awk versions
# - assert that stdout is identical
# - create data frames and publish results
#   - leave holes for Python, other shells, etc.

set -o nounset
set -o pipefail
set -o errexit

readonly OSH_CC=_bin/osh_eval.opt.stripped

TIMEFORMAT='%U'

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
  local iters=10

  #local in=README.md  # breaks on the * characters!
  local in=configure  # still doesn't work because of / and \ chars

  local out=_tmp/compute
  mkdir -p $out

  echo --- python
  time benchmarks/compute/word_freq.py $iters < $in | sort -n > $out/py.txt

  # TODO: bash isn't correct!
  #for sh in $OSH_CC; do
  for sh in bash $OSH_CC; do
    # 2 seconds
    echo --- $sh
    time $sh benchmarks/compute/word_freq.sh $iters < $in | sort -n > $out/$(basename $sh).txt
  done

  md5sum $out/*
}

# TODO:
# - do both integers and strings

bubble-sort-demo() {
  if false; then
      cat >in.txt <<EOF
a
b
 A
 Z
EOF
  fi

  seq 200 | shuf > in.txt

  local in=in.txt
  #local in=INSTALL.txt
  #local in=configure


  local out=_tmp/compute/bubble-sort
  mkdir -p $out

  echo --- python
  time benchmarks/compute/bubble_sort.py < $in > $out/py.txt

  for sh in bash $OSH_CC; do
    # 2 seconds
    echo --- $sh
    time $sh benchmarks/compute/bubble_sort.sh < $in > $out/$(basename $sh).txt
  done

  echo
  md5sum $out/*
  wc -l $out/*
}

palindrome-testdata() {
  for i in $(seq 1000); do
    cat <<EOF
foo
a
tat
cat

noon
amanaplanacanalpanama

μ
-μ-
EOF

  done
}

# Hm osh is a little slower

palindrome-demo() {
  local out=_tmp/compute/palindrome
  mkdir -p $out

  local in=$out/testdata.txt
  palindrome-testdata > $in

  #local in=_tmp/u.txt

  echo --- python
  time benchmarks/compute/palindrome.py < $in > $out/py.txt

  # Hm how does OSH respect this ???   I don't get it yet.
  #LANG=C

  for sh in bash $OSH_CC; do
    echo --- $sh
    time benchmarks/compute/palindrome.sh < $in > $out/$(basename $sh).txt
  done

  echo
  md5sum $out/*.txt
  wc -l $out/*.txt
  #cat $out/*.txt
}

#
# Also see benchmarks/parse-help.sh all
# Maybe fold that in here?
#

"$@"

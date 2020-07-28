#!/bin/bash
#
# Compare operations on data structures, with little I/O: strings, array,
# associative arrays, integers.
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
# - palindrome: string, slicing, unicode
#
# Also:
# - benchmarks/parse-help: realistic string processing.
#   Fold that in here.
#
# TODO:
# - consistent task parameterization
#   - iters is always the first argument
#   - mode:
#     - bubble_sort has int/bytes
#     - palindrome has unicode/bytes
#   - problem size, which is different than iters
#     - bubble sort: array length, to test complexity of array indexing
#     - palindrome: longer lines, to test complexity of unicode/byte slicing
#     - word_freq: more unique words, to test complexity of assoc array
# - write awk versions of each benchmark (could be contributed)
# - assert that stdout is identical
# - create data frames and publish results
#   - leave holes for Python, other shells, etc.

set -o nounset
set -o pipefail
set -o errexit

readonly OSH_CC=_bin/osh_eval.opt.stripped

TIMEFORMAT='%U'

# task_name,iter,args
tasks() {
  cat <<EOF
fib py   200 44
fib bash 200 44
fib dash 200 44
fib $OSH_CC 200 44
EOF
}

# We also want:
#   status, elapsed
#   host_name, host_hash (we don't want to test only fast machines)
#   shell_name, shell_hash (which records version.  Make sure osh --version works)
#     or really runtime_name and runtime_hash
#   task, task args -- I guess these can be space separated
#   stdout md5sum -- so it's correct!  Because I did catch some problems earlier.

compute-task() {
  # TODO: follow parser-task, and get all the args above.
  # And also need a shell functions to save the stdout md5sum?  Needs to be a
  # field too.  benchmarks/time.py gets a bunch of --field arguments.  Does it
  # need to be expanded for md5sum?
  # osh-runtime uses ${TIME_PREFIX[@]} $sh_path > STDOUT.txt

  local name=$1
  local runtime=$2
  shift 2

  local out=_tmp/compute/$name
  mkdir -p $out

  local -a TIME_PREFIX=(benchmarks/time_.py --tsv --append -o $out/times.tsv)

  case $runtime in 
    (py)
      "${TIME_PREFIX[@]}" --stdout $out/py.txt --field $runtime -- \
        benchmarks/compute/$name.py "$@"
      ;;
    (*sh | *osh*)
      local file=$(basename $runtime)
      "${TIME_PREFIX[@]}" --stdout $out/$file.txt --field $runtime -- \
        $runtime benchmarks/compute/$name.sh "$@" 
      ;;
  esac
}

fib-all() {
  local times=_tmp/compute/fib/times.tsv
  rm -f $times

  tasks | while read name runtime args; do
    compute-task $name $runtime $args  # relies on splitting
  done
  #md5sum _tmp/compute/fib/*

  wc -l _tmp/compute/fib/*
  cat $times
}

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

# TODO: Fix the OSH comparison operator!  It gives the wrong answer and
# completes quickly.

bubble-sort-demo() {
  seq 200 | shuf > in.txt

  local in=in.txt
  #local in=INSTALL.txt
  #local in=configure

  local out=_tmp/compute/bubble-sort
  mkdir -p $out

  for mode in int bytes; do
    echo === $mode

    echo --- python
    time benchmarks/compute/bubble_sort.py $mode < $in > $out/py.txt

    for sh in bash $OSH_CC; do
      # 2 seconds
      echo --- $sh
      time $sh benchmarks/compute/bubble_sort.sh $mode < $in > $out/$(basename $sh).txt
    done

    echo
    md5sum $out/*
    wc -l $out/*
  done
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

  for mode in unicode bytes; do
    echo === $mode

    echo --- python
    time benchmarks/compute/palindrome.py $mode < $in > $out/py.txt

    # Hm how does OSH respect this ???   I don't get it yet.
    #LANG=C

    for sh in bash $OSH_CC; do
      echo --- $sh
      time benchmarks/compute/palindrome.sh $mode < $in > $out/$(basename $sh).txt
    done

    echo
    md5sum $out/*.txt
    wc -l $out/*.txt
    #cat $out/*.txt

  done
}

"$@"

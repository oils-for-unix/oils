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
fib-tasks() {
  cat <<EOF
fib python   200 44
fib bash     200 44
fib dash     200 44
fib $OSH_CC  200 44
EOF
}

word_freq-tasks() {
  cat <<EOF
word_freq python   10 configure
word_freq bash     10 configure
word_freq $OSH_CC  10 configure
EOF
}

# We also want:
#   status, elapsed
#   host_name, host_hash (we don't want to test only fast machines)
#   shell_name, shell_hash (which records version.  Make sure osh --version works)
#     or really runtime_name and runtime_hash
#   task, task args -- I guess these can be space separated
#   stdout md5sum -- so it's correct!  Because I did catch some problems earlier.

readonly -a TIME_PREFIX=(benchmarks/time_.py --tsv --append)

fib-one() {
  # TODO: follow parser-task, and get all the args above.
  # And also need a shell functions to save the stdout md5sum?  Needs to be a
  # field too.  benchmarks/time.py gets a bunch of --field arguments.  Does it
  # need to be expanded for md5sum?
  # osh-runtime uses ${TIME_PREFIX[@]} $sh_path > STDOUT.txt

  local name=$1
  local runtime=$2
  shift 2

  local ext
  case $runtime in 
    (python)
      ext='py'
      ;;
    (*sh | *osh*)
      ext='sh'
      ;;
  esac

  $runtime benchmarks/compute/$name.$ext "$@"
}

word_freq-one() {
  local name=${1:-word_freq}
  local runtime=$2

  local iters=${3:-10}
  local in=${4:-configure}  # input

  local ext
  case $runtime in 
    (python)
      ext='py'
      ;;
    (*sh | *osh*)
      ext='sh'
      ;;
  esac

  $runtime benchmarks/compute/word_freq.$ext $iters < $in | sort -n
}

#
# Helpers
#

word-freq-all() { task-all word_freq; }
fib-all() { task-all fib; }

task-all() {
  local name=$1

  local out=_tmp/compute/$name
  mkdir -p $out

  local times=$out/times.tsv
  rm -f $times

  # header
  echo $'status\telapsed\tstdout_md5sum\truntime\ttask_name\ttask_args' > $times

  local name=${1:-'word-freq'}

  ${name}-tasks | while read _ runtime args; do
    local file
    case $runtime in 
      (python)
        file='py'
        ;;
      (*sh | *osh*)
        file=$(basename $runtime)
        ;;
    esac

    # join args into a single field
    "${TIME_PREFIX[@]}" \
      --stdout $out/$file.txt -o $out/times.tsv \
      --field $runtime --field "$name" --field "$args" -- \
      $0 ${name}-one "$name" "$runtime" $args  # relies on splitting
  done

  #wc -l _tmp/compute/word_freq/*
  tree $out
  cat $times
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

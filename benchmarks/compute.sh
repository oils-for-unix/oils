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

bubble_sort-tasks() {
  cat <<EOF
bubble_sort python   int
bubble_sort python   bytes
bubble_sort bash     int
bubble_sort bash     bytes
bubble_sort $OSH_CC  int
bubble_sort $OSH_CC  bytes
EOF
}

palindrome-tasks() {
  cat <<EOF
palindrome python   unicode
palindrome python   bytes
palindrome bash     unicode
palindrome bash     bytes
palindrome $OSH_CC  unicode
palindrome $OSH_CC  bytes
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

ext() {
  local ext
  case $runtime in 
    (python)
      echo 'py'
      ;;
    (*sh | *osh*)
      echo 'sh'
      ;;
  esac
}

fib-one() {
  ### Run one fibonacci task

  local name=$1
  local runtime=$2
  shift 2

  $runtime benchmarks/compute/$name.$(ext $runtime) "$@"
}

word_freq-one() {
  ### Run one word_freq task (hash tables)

  local name=${1:-word_freq}
  local runtime=$2

  local iters=${3:-10}
  local in=${4:-configure}  # input

  $runtime benchmarks/compute/word_freq.$(ext $runtime) $iters < $in | sort -n
}

bubble_sort-one() {
  ### Run one bubble_sort task (arrays)

  local name=${1:-bubble_sort}
  local runtime=$2
  local mode=${3:-int}

  $runtime benchmarks/compute/bubble_sort.$(ext $runtime) $mode \
     < _tmp/compute/$name/testdata.txt
}

palindrome-one() {
  ### Run one palindrome task (strings)

  local name=${1:-palindrome}
  local runtime=$2
  local mode=${3:-unicode}

  $runtime benchmarks/compute/palindrome.$(ext $runtime) $mode \
    < _tmp/compute/$name/testdata.txt
}

#
# Helpers
#

fib-all() { task-all fib; }
word_freq-all() { task-all word_freq; }

# TODO: Fix the OSH comparison operator!  It gives the wrong answer and
# completes quickly.
bubble_sort-all() { task-all bubble_sort; }

# Hm osh is a little slower here
palindrome-all() { task-all palindrome; }

task-all() {
  local name=$1

  local out=_tmp/compute/$name
  mkdir -p $out

  local times=$out/times.tsv
  rm -f $times

  # header
  echo $'status\telapsed\tstdout_md5sum\truntime\ttask_name\ttask_args' > $times

  local name=${1:-'word-freq'}

  local task_id=0

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

    #log "runtime=$runtime args=$args"

    # join args into a single field
    "${TIME_PREFIX[@]}" \
      --stdout $out/$task_id.txt -o $out/times.tsv \
      --field $runtime --field "$name" --field "$args" -- \
      $0 ${name}-one "$name" "$runtime" $args  # relies on splitting

    task_id=$((task_id + 1))
  done

  #wc -l _tmp/compute/word_freq/*
  tree $out
  cat $times
}

#
# Testdata
#

bubble_sort-testdata() {
  local out='_tmp/compute/bubble_sort'
  mkdir -p $out
  seq 200 | shuf > $out/testdata.txt
  wc -l $out/testdata.txt
}

palindrome-testdata() {
  local out=_tmp/compute/palindrome
  mkdir -p $out

  # TODO: Use iters?

  for i in $(seq 500); do
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

  done > $out/testdata.txt
  
  wc -l $out/testdata.txt
}

"$@"

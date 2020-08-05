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
# - bubble_sort: indexed array (bash uses a linked list?)
# - palindrome: string, slicing, unicode
# - parse-help: realistic shell-only string processing, which I didn't write.
#
# TODO:
# - vary problem size, which is different than iters
#   - bubble sort: array length, to test complexity of array indexing
#   - palindrome: longer lines, to test complexity of unicode/byte slicing
#   - word_freq: more unique words, to test complexity of assoc array
# - write awk versions of each benchmark (could be contributed)
# - assert that stdout is identical
# - create data frames and publish results
#   - leave holes for Python, other shells, etc.

set -o nounset
set -o pipefail
set -o errexit

readonly BASE_DIR=_tmp/compute
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
  # Note: this is quadratic, but bubble sort itself is quadratic!

  cat <<EOF
bubble_sort python   int   200
bubble_sort python   bytes 200
bubble_sort bash     int   200
bubble_sort bash     bytes 200
bubble_sort $OSH_CC  int   200
bubble_sort $OSH_CC  bytes 200
EOF
}

# Arrays are doubly linked lists in bash!  With a LASTREF hack to avoid being
# quadratic.  
#
# See array_reference() in array.c in bash.  It searches both back and
# forward.  Every cell has its index, a value, a forward pointer, and a back
# pointer.
#
# You need pretty high N to see the quadratic behavior though!

# NOTE: osh is also slower with linear access, but not superlinear!

array_ref-tasks() {
  #for sh in bash "$OSH_CC"; do
  for sh in bash; do
    for mode in seq random; do
      cat <<EOF
array_ref $sh     $mode    10000
array_ref $sh     $mode    20000
array_ref $sh     $mode    30000
array_ref $sh     $mode    40000
EOF
    done
  done

#array_ref $OSH_CC  seq    5000
#array_ref $OSH_CC  seq    10000
#array_ref $OSH_CC  random 5000
#array_ref $OSH_CC  random 10000
#EOF
}

palindrome-tasks() {
  cat <<EOF
palindrome python   unicode _
palindrome python   bytes   _
palindrome bash     unicode _
palindrome bash     bytes   _
palindrome $OSH_CC  unicode _
palindrome $OSH_CC  bytes   _
EOF
}

parse-help-tasks() {
  cat <<EOF
parse-help bash     ls-short _
parse-help bash     ls       _
parse-help bash     mypy     _
parse-help $OSH_CC  ls-short _
parse-help $OSH_CC  ls       _
parse-help $OSH_CC  mypy     _
EOF
}

# We also want:
#   status, elapsed
#   host_name, host_hash (we don't want to test only fast machines)
#   shell_name, shell_hash (which records version.  Make sure osh --version works)
#     or really runtime_name and runtime_hash
#   task, task args -- I guess these can be space separated
#   stdout md5sum -- so it's correct!  Because I did catch some problems earlier.

readonly -a TIME_PREFIX=(benchmarks/time_.py --tsv --append --rusage)

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
  local n=${4:-100}

  $runtime benchmarks/compute/bubble_sort.$(ext $runtime) $mode \
     < $BASE_DIR/$name/testdata-$n.txt
}

# OSH is like 10x faster here!
array_ref-one() {
  ### Run one array_ref task (arrays)

  local name=${1:-bubble_sort}
  local runtime=$2
  local mode=${3:-seq}
  local n=${4:-100}

  seq $n | shuf | $runtime benchmarks/compute/array_ref.$(ext $runtime) $mode
}

palindrome-one() {
  ### Run one palindrome task (strings)

  local name=${1:-palindrome}
  local runtime=$2
  local mode=${3:-unicode}

  $runtime benchmarks/compute/palindrome.$(ext $runtime) $mode \
    < $BASE_DIR/$name/testdata.txt
}

parse-help-one() {
  ### Run one palindrome task (strings, real code)

  local name=${1:-parse-help}
  local runtime=$2
  local workload=${3:-}

  $runtime benchmarks/parse-help/pure-excerpt.sh _parse_help - \
    < benchmarks/parse-help/$workload.txt
}

#
# Helpers
#

fib-all() { task-all fib; }
word_freq-all() { task-all word_freq; }

# TODO: Fix the OSH comparison operator!  It gives the wrong answer and
# completes quickly.
bubble_sort-all() { task-all bubble_sort; }

# Array that is not quadratic
array_ref-all() { task-all array_ref; }

# Hm osh is a little slower here
palindrome-all() { task-all palindrome; }

parse-help-all() { task-all parse-help; }

task-all() {
  local name=$1

  local out=$BASE_DIR/$name
  mkdir -p $out

  local times=$out/times.tsv
  rm -f $times

  # header
  echo $'status\telapsed\tuser_time\tsys_time\tmax_rss\tstdout_md5sum\truntime\ttask_name\targ1\targ2' > $times

  local name=${1:-'word-freq'}

  local task_id=0

  ${name}-tasks | while read _ runtime arg1 arg2; do
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
      --stdout $out/stdout-$task_id.txt -o $out/times.tsv \
      --field $runtime --field "$name" --field "$arg1" --field "$arg2" -- \
      $0 ${name}-one "$name" "$runtime" "$arg1" "$arg2"

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
  local out=$BASE_DIR/bubble_sort
  mkdir -p $out

  # TODO: Make these deterministic for more stable benchmarks?
  for n in 100 200 300 400; do
    seq $n | shuf > $out/testdata-$n.txt
  done

  wc -l $out/testdata-*.txt
}

palindrome-testdata() {
  local out=$BASE_DIR/palindrome
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

measure() {
  #local provenance=$1
  local raw_dir=${2:-$BASE_DIR/raw}

  fib-all
  word_freq-all
  parse-help-all

  tree $BASE_DIR
}


"$@"

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
# - parse_help: realistic shell-only string processing, which I didn't write.
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

source benchmarks/common.sh  # filter-provenance

readonly BASE_DIR=_tmp/compute
readonly OSH_CC=_bin/osh_eval.opt.stripped

TIMEFORMAT='%U'

# task_name,iter,args
fib-tasks() {
  local provenance=$1

  # Add 1 field for each of 5 fields.
  cat $provenance | filter-provenance python bash dash $OSH_CC |
  while read fields; do
    echo 'fib 200 44' | xargs -n 3 -- echo "$fields"
  done
}

word_freq-tasks() {
  local provenance=$1

  cat $provenance | filter-provenance python bash $OSH_CC |
  while read fields; do
    # Why does osh_eval differ?
    #echo 'word_freq 2 benchmarks/testdata/abuild' | xargs -n 3 -- echo "$fields"
    #echo 'word_freq 2 benchmarks/testdata/ltmain.sh' | xargs -n 3 -- echo "$fields"
    echo 'word_freq 10 configure' | xargs -n 3 -- echo "$fields"
  done
}

bubble_sort-tasks() {
  # Note: this is quadratic, but bubble sort itself is quadratic!
  local provenance=$1

  cat $provenance | filter-provenance python bash $OSH_CC |
  while read fields; do
    echo 'bubble_sort int   200' | xargs -n 3 -- echo "$fields"
    echo 'bubble_sort bytes 200' | xargs -n 3 -- echo "$fields"
  done
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
  local provenance=$1

  cat $provenance | filter-provenance bash |
  while read fields; do
    for mode in seq random; do
      for n in 10000 20000 30000 40000; do
        echo "array_ref $mode $n" | xargs -n 3 -- echo "$fields"
      done
    done
  done

#array_ref $OSH_CC  seq    5000
#array_ref $OSH_CC  seq    10000
#array_ref $OSH_CC  random 5000
#array_ref $OSH_CC  random 10000
#EOF
}

palindrome-tasks() {
  local provenance=$1

  cat $provenance | filter-provenance python bash $OSH_CC |
  while read fields; do
    echo 'palindrome unicode _' | xargs -n 3 -- echo "$fields"
    echo 'palindrome bytes   _' | xargs -n 3 -- echo "$fields"
  done
}

parse_help-tasks() {
  local provenance=$1

  cat $provenance | filter-provenance bash $OSH_CC |
  while read fields; do
    echo 'parse_help ls-short _' | xargs -n 3 -- echo "$fields"
    echo 'parse_help ls       _' | xargs -n 3 -- echo "$fields"
    echo 'parse_help mypy     _' | xargs -n 3 -- echo "$fields"
  done
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
     < $BASE_DIR/tmp/$name/testdata-$n.txt
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
    < $BASE_DIR/tmp/$name/testdata.txt
}

parse_help-one() {
  ### Run one palindrome task (strings, real code)

  local name=${1:-parse_help}
  local runtime=$2
  local workload=${3:-}

  $runtime benchmarks/parse-help/pure-excerpt.sh _parse_help - \
    < benchmarks/parse-help/$workload.txt
}

#
# Helpers
#

fib-all() { task-all fib "$@"; }
word_freq-all() { task-all word_freq "$@"; }

# TODO: Fix the OSH comparison operator!  It gives the wrong answer and
# completes quickly.
bubble_sort-all() { task-all bubble_sort "$@"; }

# Array that is not quadratic
array_ref-all() { task-all array_ref "$@"; }

# Hm osh is a little slower here
palindrome-all() { task-all palindrome "$@"; }

parse_help-all() { task-all parse_help "$@"; }

task-all() {
  local task_name=$1
  local provenance=$2
  local raw_dir=$3  # put files to save in benchmarks-data repo here

  local tmp_dir=$BASE_DIR/tmp/$task_name

  local filename=$(basename $provenance)
  local prefix=${filename%.provenance.txt}  # strip suffix

  local times_tsv=$raw_dir/$task_name/$prefix.times.tsv
  rm -f $times_tsv

  mkdir -p $tmp_dir $raw_dir/$task_name

  # header
  echo $'status\telapsed_secs\tuser_secs\tsys_secs\tmax_rss_KiB\tstdout_md5sum\thost_name\thost_hash\truntime_name\truntime_hash\ttask_name\targ1\targ2' > $times_tsv

  local task_id=0

  ${task_name}-tasks $provenance > $tmp_dir/tasks.txt

  cat $tmp_dir/tasks.txt |
  while read _ host host_hash runtime runtime_hash _ arg1 arg2; do
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
      --stdout $tmp_dir/stdout-$file-$arg1-$arg2.txt -o $times_tsv \
      --field "$host" --field "$host_hash" \
      --field $runtime --field $runtime_hash \
      --field "$task_name" --field "$arg1" --field "$arg2" -- \
      $0 ${task_name}-one "$task_name" "$runtime" "$arg1" "$arg2"

    task_id=$((task_id + 1))
  done

  #wc -l _tmp/compute/word_freq/*
  tree $tmp_dir
  cat $times_tsv
}

#
# Testdata
#

bubble_sort-testdata() {
  local out=$BASE_DIR/tmp/bubble_sort
  mkdir -p $out

  # TODO: Make these deterministic for more stable benchmarks?
  for n in 100 200 300 400; do
    seq $n | shuf > $out/testdata-$n.txt
  done

  wc -l $out/testdata-*.txt
}

palindrome-testdata() {
  local out=$BASE_DIR/tmp/palindrome
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
  local provenance=$1
  local raw_dir=${2:-$BASE_DIR/raw}  # ../benchmark-data/compute

  mkdir -p $BASE_DIR/{tmp,raw,stage1} $raw_dir

  fib-all $provenance $raw_dir
  word_freq-all $provenance $raw_dir
  parse_help-all $provenance $raw_dir

  bubble_sort-testdata
  palindrome-testdata

  bubble_sort-all $provenance $raw_dir

  # INCORRECT, but still run it
  palindrome-all $provenance $raw_dir

  # array_ref takes too long to show quadratic behavior, and that's only
  # necessary on 1 machine.  I think I will make a separate blog post,
  # if anything.

  tree $raw_dir
}

stage1() {
  local raw_dir=${1:-$BASE_DIR/raw}
  local out_dir=$BASE_DIR/stage1
  mkdir -p $out_dir

  local times_tsv=$out_dir/times.tsv

  local -a raw=()

  for metric in fib word_freq parse_help bubble_sort palindrome; do
    local dir=$raw_dir/$metric

    # Globs are in lexicographical order, which works for our dates.
    local -a a=($dir/$MACHINE2.*.times.tsv)
    local -a b=($dir/$MACHINE2.*.times.tsv)  # HACK for now

    # take the latest file
    raw+=(${a[-1]} ${b[-1]})
  done
  csv-concat ${raw[@]} > $times_tsv
  wc -l $times_tsv
}

tsv2html() {
  csv2html --tsv "$@"
}

print-report() {
  local in_dir=$1

  benchmark-html-head 'OSH Compute Performance'

  cat <<EOF
  <body class="width60">
    <p id="home-link">
      <a href="/">oilshell.org</a>
    </p>
EOF
  cmark <<EOF

## OSH Compute Performance

Running time and memory usage of programs that test data structures (as opposed
to I/O).

Memory usage is measured in MB (powers of 10), not MiB (powers of 2).

EOF

  cmark <<EOF
### fibonacci (integers)

- arg1: number of repetitions
- arg2: the N in fib(N)
EOF

  tsv2html $in_dir/fib.tsv

  cmark <<EOF
### word_freq (associative arrays / hash tables)

- arg1: number of repetitions
- arg2: the file (varies size of hash table)
EOF

  tsv2html $in_dir/word_freq.tsv

  cmark <<EOF
### parse_help (strings, real code)

- arg1: file to parse
EOF

  tsv2html $in_dir/parse_help.tsv

  cmark <<EOF
### bubble_sort (array of integers, arrays of strings)

- arg1: type of array
- arg2: length of array
EOF

  tsv2html $in_dir/bubble_sort.tsv

  # Comment out until checksum is fixed
if false; then
  cmark <<EOF
### palindrome (byte strings, unicode strings)

- arg1: type of string
- arg2: TODO: length of string
EOF

  tsv2html $in_dir/palindrome.tsv

fi

  cmark <<EOF
### Interpreter and Host Details
EOF

  tsv2html $in_dir/shells.tsv
  tsv2html $in_dir/hosts.tsv

  cmark <<EOF
### Details
EOF

  tsv2html $in_dir/details.tsv


  cat <<EOF
  </body>
</html>
EOF
}


"$@"

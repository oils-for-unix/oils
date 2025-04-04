#!/usr/bin/env bash
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
# - for_loop: 2025 update, taken from benchmarks/ysh-for.sh
# - word_freq: hash table / assoc array (OSH uses a vector<pair<>> now!)
#              also integer counter
# - bubble_sort: indexed array (bash uses a linked list?)
# - palindrome: string, slicing, unicode
# - parse_help: realistic shell-only string processing, which I didn't write.
#
# TODO:
# - Fix the BUGS
#   - palindrome doesn't work?  Unicode?  Does UTF-8 decode
#   - bubble sort depend on locale too - there is an LC_ALL here
#
# - This file is annoying to TEST
#   - to add to it, you also have to change benchmarks/report.R
#   - and there is a loop in 'stage1' as well
#   - why can't it behave like other benchmarks?
#   - they are using this "big table" pattern

# - vary problem size, which is different than iters
#   - bubble sort: array length, to test complexity of array indexing
#   - palindrome: longer lines, to test complexity of unicode/byte slicing
#   - word_freq: more unique words, to test complexity of assoc array
# - for_loop and fib are kinda similar
#   - maybe for_loop can introduce some conditionals
#
# - other languages
#   - awk, mawk, etc.
#   - we are going for Awk speed!
#
# Questions to answer
# - Can fast bytecode runtime be as fast as Python?
#   - measurement issue: Python kills at fib/for_loop - it's mostly process
#     startup time
# - bubble_sort and word_freq are a bit more work 
#   - can add YSH versions of those
#   - I wonder if they are testing data structures or the actual interpreter
#   loop though
#   - it's possible that speeding up the interpreter loop doesn't help much
# - the real motivations behind bytecode:
#   - to fix 'break continue'
#   - add coroutine support too - that suspends and resumes a frame, which we
#   can't do

set -o nounset
set -o pipefail
set -o errexit

REPO_ROOT=$(cd $(dirname $0)/.. && pwd)
readonly REPO_ROOT

source benchmarks/common.sh  # filter-provenance
source test/tsv-lib.sh  # tsv2html

readonly BASE_DIR=_tmp/compute

# Stabilize 'sort' output across machines (ugh locales!)
export LC_ALL=C

TIMEFORMAT='%U'

# task_name,iter,args
hello-tasks() {
  local provenance=$1

  # Add 1 field for each of 5 fields.
  cat $provenance | filter-provenance python2 bash dash "$OSH_CPP_REGEX" |
  while read fields; do
    echo 'hello _ _' | xargs -n 3 -- echo "$fields"
  done
}

# task_name,iter,args
fib-tasks() {
  local provenance=$1

  local runtime_regex='_bin/cxx-opt/(osh|ysh)'

  # Add 1 field for each of 5 fields.
  cat $provenance | filter-provenance python2 bash dash "$runtime_regex" |
  while read fields; do
    echo 'fib 200 44' | xargs -n 3 -- echo "$fields"
  done
}

# task_name,iter,args
for_loop-tasks() {
  local provenance=$1

  # bumpleak segfaults on for_loop!  Probably because it runs out of memory
  local runtime_regex='_bin/cxx-opt/(osh|ysh)'

  # TODO: add YSH too
  cat $provenance | filter-provenance python2 bash dash "$runtime_regex" |
  while read fields; do
    echo 'for_loop 50000 _' | xargs -n 3 -- echo "$fields"
  done
}

word_freq-tasks() {
  local provenance=$1

  cat $provenance | filter-provenance python2 bash "$OSH_CPP_REGEX" |
  while read fields; do
    # BUG: oils-for-unix differs on these two.  Looks like it's related to
    # backslashes!
    #echo 'word_freq 10 benchmarks/testdata/abuild' | xargs -n 3 -- echo "$fields"
    #echo 'word_freq 2 benchmarks/testdata/ltmain.sh' | xargs -n 3 -- echo "$fields"
    echo 'word_freq 10 configure' | xargs -n 3 -- echo "$fields"
  done
}

assoc_array-tasks() {
  local provenance=$1

  cat $provenance | filter-provenance python2 bash "$OSH_CPP_REGEX" |
  while read fields; do
    for n in 1000 2000 3000; do
      echo "word_freq 10 $n" | xargs -n 3 -- echo "$fields"
    done
  done
}

bubble_sort-tasks() {
  # Note: this is quadratic, but bubble sort itself is quadratic!
  local provenance=$1

  cat $provenance | filter-provenance python2 bash "$OSH_CPP_REGEX" |
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

  cat $provenance | filter-provenance python2 bash "$OSH_CPP_REGEX" |
  while read fields; do
    echo 'palindrome unicode _' | xargs -n 3 -- echo "$fields"
    echo 'palindrome bytes   _' | xargs -n 3 -- echo "$fields"
  done
}

parse_help-tasks() {
  local provenance=$1

  cat $provenance | filter-provenance bash "$OSH_CPP_REGEX" |
  while read fields; do
    echo 'parse_help ls-short _' | xargs -n 3 -- echo "$fields"
    echo 'parse_help ls       _' | xargs -n 3 -- echo "$fields"
    echo 'parse_help mypy     _' | xargs -n 3 -- echo "$fields"
  done
}

ext() {
  local ext
  case $runtime in 
    python2)
      echo 'py'
      ;;
    *ysh*)
      echo 'ysh'
      ;;
    *sh | *osh*)
      echo 'sh'
      ;;
  esac
}

word_freq-one() {
  ### Run one word_freq task (hash tables)

  local name=${1:-word_freq}
  local runtime=$2

  local iters=${3:-10}
  local in=${4:-configure}  # input

  $runtime benchmarks/compute/word_freq.$(ext $runtime) $iters < $in | sort -n
}

assoc_array-one() {
  ### Run word_freq with seq

  local name=${1:-word_freq}
  local runtime=$2

  local iters=${3:-10}
  local n=${4:-10} 

  # shuf so we don't get the bash optimization
  seq $n | shuf |
  $runtime benchmarks/compute/word_freq.$(ext $runtime) $iters | sort -n
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

hello-all() { task-all hello "$@"; }
fib-all() { task-all fib "$@"; }
for_loop-all() { task-all for_loop "$@"; }
word_freq-all() { task-all word_freq "$@"; }
assoc_array-all() { task-all assoc_array "$@"; }

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
  local host_job_id=$3
  local out_dir=$4  # put files to save in benchmarks-data repo here

  local tmp_dir=$BASE_DIR/tmp/$task_name

  local times_tsv=$out_dir/$task_name/$host_job_id.times.tsv
  rm -f $times_tsv

  mkdir -p $tmp_dir $out_dir/$task_name

  banner "*** $task_name ***"

  # header
  tsv-row \
    status elapsed_secs user_secs sys_secs max_rss_KiB \
    stdout_md5sum \
    host_name host_hash \
    runtime_name runtime_hash \
    task_name arg1 arg2 stdout_filename > $times_tsv

  local task_id=0

  ${task_name}-tasks $provenance > $tmp_dir/tasks.txt

  cat $tmp_dir/tasks.txt |
  while read _ host host_hash runtime runtime_hash _ arg1 arg2; do
    local file
    case $runtime in 
      (python2)
        file='py'
        ;;
      (*sh | *osh*)
        file=$(basename $runtime)
        ;;
    esac

    #log "runtime=$runtime args=$args"

    local stdout_filename="stdout-$file-$arg1-$(basename $arg2).txt"

    # Measurement BUG!  This makes dash have the memory usage of bash!
    # It's better to get argv into the shell.

    local -a cmd
    case $task_name in
      (hello|fib|for_loop)
        # Run it DIRECTLY, do not run $0.  Because we do NOT want to fork bash
        # then dash, because bash uses more memory.
        cmd=($runtime benchmarks/compute/$task_name.$(ext $runtime) "$arg1" "$arg2")
        ;;
      (*)
        cmd=($0 ${task_name}-one "$task_name" "$runtime" "$arg1" "$arg2")
        ;;
    esac

    # join args into a single field
    time-tsv -o $times_tsv --append \
      --stdout $tmp_dir/$stdout_filename \
      --rusage \
      --field "$host" --field "$host_hash" \
      --field $runtime --field $runtime_hash \
      --field "$task_name" --field "$arg1" --field "$arg2" \
      --field "$stdout_filename" -- \
      "${cmd[@]}"

    task_id=$((task_id + 1))
  done

  #wc -l _tmp/compute/word_freq/*
  maybe-tree $tmp_dir
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
  local host_job_id=$2
  local out_dir=${3:-$BASE_DIR/raw}  # ../benchmark-data/compute

  mkdir -p $BASE_DIR/{tmp,raw,stage1} $out_dir

  # set -x
  hello-all $provenance $host_job_id $out_dir
  fib-all $provenance $host_job_id $out_dir

  for_loop-all $provenance $host_job_id $out_dir

  # TODO: doesn't work because we would need duplicate logic in stage1
  #if test -n "${QUICKLY:-}"; then
  #  return
  #fi
  
  word_freq-all $provenance $host_job_id $out_dir
  parse_help-all $provenance $host_job_id $out_dir

  bubble_sort-testdata
  palindrome-testdata

  bubble_sort-all $provenance $host_job_id $out_dir

  # INCORRECT, but still run it
  palindrome-all $provenance $host_job_id $out_dir

  # array_ref takes too long to show quadratic behavior, and that's only
  # necessary on 1 machine.  I think I will make a separate blog post,
  # if anything.

  maybe-tree $out_dir
}

soil-run() {
  ### Run it on just this machine, and make a report

  rm -r -f $BASE_DIR
  mkdir -p $BASE_DIR

  # Test the one that's IN TREE, NOT in ../benchmark-data
  local -a oils_bin=(
    _bin/cxx-opt/osh _bin/cxx-opt+bumpleak/osh _bin/cxx-opt/mycpp-souffle/osh 
    _bin/cxx-opt/ysh _bin/cxx-opt+bumpleak/ysh _bin/cxx-opt/mycpp-souffle/ysh 
  )
  ninja "${oils_bin[@]}"

  local single_machine='no-host'

  local job_id
  job_id=$(benchmarks/id.sh print-job-id)

  # Only measure what's in the Docker image
  # - The Soil 'benchmarks' job uses the 'cpp' Docker image, which doesn't have
  #   layer-cpython, ../oil_DEPS/cpython-full
  # - It also doesn't have mksh or zsh

  benchmarks/id.sh shell-provenance-2 \
    $single_machine $job_id _tmp \
    bash dash python2 "${oils_bin[@]}"

  local provenance=_tmp/provenance.txt
  local host_job_id="$single_machine.$job_id"

  measure $provenance $host_job_id

  # Make it run on one machine
  stage1 '' $single_machine

  benchmarks/report.sh stage2 $BASE_DIR
  benchmarks/report.sh stage3 $BASE_DIR
}


test-report() {
  # Make it run on one machine
  stage1 '' no-host

  benchmarks/report.sh stage2 $BASE_DIR
  benchmarks/report.sh stage3 $BASE_DIR
}

stage1() {
  local raw_dir=${1:-$BASE_DIR/raw}

  # This report works even if we only have one machine
  local single_machine=${2:-}

  local out_dir=$BASE_DIR/stage1
  mkdir -p $out_dir

  local times_tsv=$out_dir/times.tsv

  local -a raw=()

  # TODO: We should respect QUICKLY=1
  for metric in hello fib for_loop word_freq parse_help bubble_sort palindrome; do
    local dir=$raw_dir/$metric

    if test -n "$single_machine"; then
      local -a a=($dir/$single_machine.*.times.tsv)
      raw+=(${a[-1]})
    else
      # Globs are in lexicographical order, which works for our dates.
      local -a a=($dir/$MACHINE1.*.times.tsv)
      local -a b=($dir/$MACHINE2.*.times.tsv)  # HACK for now

      # take the latest file
      raw+=(${a[-1]} ${b[-1]})
    fi

  done
  csv-concat ${raw[@]} > $times_tsv
  wc -l $times_tsv
}

print-report() {
  local in_dir=$1

  benchmark-html-head 'OSH Compute Performance'

  cat <<EOF
  <body class="width60">
    <p id="home-link">
      <a href="/">oils.pub</a>
    </p>
EOF
  cmark <<EOF

## OSH Compute Performance

Running time and memory usage of programs that test data structures (as opposed
to I/O).

Memory usage is measured in MB (powers of 10), not MiB (powers of 2).

Source code: [oil/benchmarks/compute](https://github.com/oilshell/oil/tree/master/benchmarks/compute)

EOF

  cmark <<EOF
### hello (minimal startup)

EOF

  tsv2html $in_dir/hello.tsv

  cmark <<EOF
### fibonacci (integers)

- arg1: number of repetitions
- arg2: the N in fib(N)
EOF

  tsv2html $in_dir/fib.tsv

  cmark <<EOF
### for loop

- arg2: the N to sum
EOF

  tsv2html $in_dir/for_loop.tsv

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

  cmark <<EOF
### Stdout Files
EOF

  tsv2html $in_dir/stdout_files.tsv


  cat <<EOF
  </body>
</html>
EOF
}

control-flow() {
  ### Reproduce OSH perf bug because of C++ exceptions

  # do_neither:  0.288 dash, 0.872 bash, 0.865 OSH
  # do_continue: 0.310 dash, 1.065 bash, 2.313 OSH
  # do_break:    0.222 dash, 0.712 bash, 1.430 OSH

  local osh=_bin/cxx-opt/osh
  #set -x

  ninja $osh

  for func in do_neither do_continue do_break; do
    echo "=== $func"
    echo
    for sh in dash bash $osh; do
      echo "--- $sh"
      # TIMEFORMAT above
      time $sh benchmarks/compute/control_flow.sh $func 500
      echo
    done
  done
}

word-split() {
  ### Test word splitting perf
  export OILS_GC_STATS=${1:-}

  # do_neither:  0.288 dash, 0.872 bash, 0.865 OSH
  # do_continue: 0.310 dash, 1.065 bash, 2.313 OSH
  # do_break:    0.222 dash, 0.712 bash, 1.430 OSH

  local osh=_bin/cxx-opt/osh
  #set -x

  ninja $osh

  #local filename=README.md

  # Hm our word splitting actually isn't that slow?
  # TODO: measure allocs too?

  # Hm allocating over a million objects, but it's faster than bash
  # Most are in the pools

  local filename=benchmarks/testdata/configure-coreutils

  for func in default_ifs other_ifs; do
    echo "=== $func"
    echo
    for sh in dash bash $osh; do
      echo "--- $sh"
      # TIMEFORMAT above
      time $sh benchmarks/compute/word_split.sh $func $filename
      echo
    done
  done
}

"$@"

#!/usr/bin/env bash
#
# Measure how fast the OSH parser is.
#
# Usage:
#   benchmarks/osh-parser.sh <function name>
#
# Examples:
#   benchmarks/osh-parser.sh soil-run
#   QUICKLY=1 benchmarks/osh-parser.sh soil-run

set -o nounset
set -o pipefail
set -o errexit

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)  # tsv-lib.sh uses this
readonly REPO_ROOT

source benchmarks/common.sh  # die
source benchmarks/cachegrind.sh  # with-cachgrind
source soil/common.sh  # find-dir-html
source test/tsv-lib.sh  # tsv2html
source test/common.sh  # die

# TODO: The raw files should be published.  In both
# ~/git/oilshell/benchmarks-data and also in the /release/ hierarchy?
readonly BASE_DIR=_tmp/osh-parser
readonly SORTED=$BASE_DIR/tmp/sorted.txt

write-sorted-manifest() {
  local files=${1:-benchmarks/osh-parser-files.txt}
  local counts=$BASE_DIR/tmp/line-counts.txt
  local csv_out=$2
  local sep=${3:-','}  # CSV or TSV

  # Remove comments and sort by line count
  grep -v '^#' $files | xargs wc -l | sort -n > $counts
    
  # Raw list of paths
  cat $counts | awk '$2 != "total" { print $2 }' > $SORTED

  # Make a CSV file from wc output
  cat $counts | awk -v sep="$sep" '
      BEGIN { print "num_lines" sep "path" }
      $2 != "total" { print $1 sep $2 }' \
      > $csv_out
}

# Called by xargs with a task row.
parser-task() {
  local out_dir=$1  # output
  local job_id=$2
  local host=$3
  local host_hash=$4
  local sh_path=$5
  local shell_hash=$6
  local script_path=$7

  echo "--- TIME $sh_path $script_path ---"

  local times_out="$out_dir/$host.$job_id.times.csv"

  local shell_name
  shell_name=$(basename $sh_path)

  # Can't use array because of set -u bug!!!  Only fixed in bash 4.4.
  extra_args=''
  case "$shell_name" in
    osh|oils-for-unix.*)
      extra_args='--ast-format none'
      ;;
  esac

  # exit code, time in seconds, host_hash, shell_hash, path.  \0
  # would have been nice here!
  # TODO: TSV
  benchmarks/time_.py \
    --append \
    --output $times_out \
    --rusage \
    --field "$host" --field "$host_hash" \
    --field "$shell_name" --field "$shell_hash" \
    --field "$script_path" -- \
    "$sh_path" -n $extra_args "$script_path" || echo FAILED
}

# Called by xargs with a task row.
# NOTE: This is very similar to the function above, except that we add
# cachegrind.  We could probably conslidate these.
cachegrind-task() {
  local out_dir=$1  # output
  local job_id=$2
  local host_name=$3
  local unused2=$4
  local sh_path=$5
  local shell_hash=$6
  local script_path=$7

  echo "--- CACHEGRIND $sh_path $script_path ---"

  local host_job_id="$host_name.$job_id"

  # NOTE: This has to match the path that the header was written to
  local times_out="$out_dir/$host_job_id.cachegrind.tsv"

  local cachegrind_out_dir="$host_job_id.cachegrind"
  mkdir -p $out_dir/$cachegrind_out_dir

  local shell_name
  shell_name=$(basename $sh_path)

  local script_name
  script_name=$(basename $script_path)

  # RELATIVE PATH
  local cachegrind_out_path="${cachegrind_out_dir}/${shell_name}-${shell_hash}__${script_name}.txt"

  # Can't use array because of set -u bug!!!  Only fixed in bash 4.4.
  extra_args=''
  case "$shell_name" in
    osh|oils-for-unix.*)
      extra_args="--ast-format none"
      ;;
  esac

  benchmarks/time_.py \
    --tsv \
    --append \
    --output $times_out \
    --rusage \
    --field "$shell_name" --field "$shell_hash" \
    --field "$script_path" \
    --field $cachegrind_out_path \
    -- \
    $0 with-cachegrind $out_dir/$cachegrind_out_path \
    "$sh_path" -n $extra_args "$script_path" || echo FAILED
}

# For each shell, print 10 script paths.
print-tasks() {
  local provenance=$1
  shift
  # rest are shells

  # Add 1 field for each of 5 fields.
  cat $provenance | filter-provenance "$@" |
  while read fields; do
    if test -n "${QUICKLY:-}"; then
      # Quick test
      head -n 2 $SORTED | xargs -n 1 -- echo "$fields"
    else
      cat $SORTED | xargs -n 1 -- echo "$fields"
    fi
  done
}

cachegrind-parse-configure-coreutils() {
  ### Similar to benchmarks/gc, benchmarks/uftrace

  local bin=_bin/cxx-opt/oils-for-unix
  ninja $bin
  local out=_tmp/parse.configure-coreutils.txt 

  local -a cmd=( 
    $bin --ast-format none -n
    benchmarks/testdata/configure-coreutils )

  time "${cmd[@]}"

  time cachegrind $out "${cmd[@]}"

  echo
  cat $out
}

cachegrind-demo() {
  #local sh=bash
  local sh=zsh

  local out_dir=_tmp/cachegrind

  mkdir -p $out_dir

  # notes:
  # - not passing --trace-children (follow execvpe)
  # - passing --xml=yes gives error: cachegrind doesn't support XML
  # - there is a log out and a details out

  valgrind --tool=cachegrind \
    --log-file=$out_dir/log.txt \
    --cachegrind-out-file=$out_dir/details.txt \
    -- $sh -c 'echo hi'

  echo
  head -n 20 $out_dir/*.txt
}

readonly NUM_TASK_COLS=6  # input columns: 5 from provenance, 1 for file

# Figure out all tasks to run, and run them.  When called from auto.sh, $2
# should be the ../benchmarks-data repo.
measure() {
  local provenance=$1
  local host_job_id=$2
  local out_dir=${3:-$BASE_DIR/raw}
  local osh_cpp=${4:-$OSH_CPP_BENCHMARK_DATA}

  local times_out="$out_dir/$host_job_id.times.csv"
  local lines_out="$out_dir/$host_job_id.lines.csv"

  mkdir -p $BASE_DIR/{tmp,raw,stage1} $out_dir

  # Files that we should measure.  Exploded into tasks.
  write-sorted-manifest '' $lines_out

  # Write Header of the CSV file that is appended to.
  # TODO: TSV
  benchmarks/time_.py --print-header \
    --rusage \
    --field host_name --field host_hash \
    --field shell_name --field shell_hash \
    --field path \
    > $times_out

  local tasks=$BASE_DIR/tasks.txt
  print-tasks $provenance "${SHELLS[@]}" $osh_cpp > $tasks

  # Run them all
  cat $tasks | xargs -n $NUM_TASK_COLS -- $0 parser-task $out_dir
}

measure-cachegrind() {
  local provenance=$1
  local host_job_id=$2
  local out_dir=${3:-$BASE_DIR/raw}
  local osh_cpp=${4:-$OSH_CPP_BENCHMARK_DATA}

  local cachegrind_tsv="$out_dir/$host_job_id.cachegrind.tsv"
  local lines_out="$out_dir/$host_job_id.lines.tsv"

  mkdir -p $BASE_DIR/{tmp,raw,stage1} $out_dir

  write-sorted-manifest '' $lines_out $'\t'  # TSV

  # TODO: This header is fragile.  Every task should print its own file with a
  # header, and then we can run them in parallel, and join them with
  # devtools/csv_concat.py

  benchmarks/time_.py --tsv --print-header \
    --rusage \
    --field shell_name --field shell_hash \
    --field path \
    --field cachegrind_out_path \
    > $cachegrind_tsv

  local ctasks=$BASE_DIR/cachegrind-tasks.txt

  # zsh weirdly forks during zsh -n, which complicates our cachegrind
  # measurement.  So just ignore it.  (This can be seen with
  # strace -e fork -f -- zsh -n $file)
  print-tasks $provenance bash dash mksh $osh_cpp > $ctasks

  cat $ctasks | xargs -n $NUM_TASK_COLS -- $0 cachegrind-task $out_dir
}

#
# Data Preparation and Analysis
#

stage1-cachegrind() {
  local raw_dir=$1
  local single_machine=$2
  local out_dir=$3
  local raw_data_csv=$4

  local maybe_host
  if test -n "$single_machine"; then
    # CI: _tmp/osh-parser/raw.no-host.$job_id
    maybe_host='no-host'
  else
    # release: ../benchmark-data/osh-parser/raw.lenny.$job_id
    #maybe_host=$(hostname)
    maybe_host=$MACHINE2  # lenny
  fi

  # Only runs on one machine
  local -a sorted=( $raw_dir/$maybe_host.*.cachegrind.tsv )
  local tsv_in=${sorted[-1]}  # latest one

  devtools/tsv_column_from_files.py \
    --new-column irefs \
    --path-column cachegrind_out_path \
    --extract-group-1 'I[ ]*refs:[ ]*([\d,]+)' \
    --remove-commas \
    $tsv_in > $out_dir/cachegrind.tsv

  echo $tsv_in >> $raw_data_csv
}

stage1() {
  local raw_dir=${1:-$BASE_DIR/raw}
  local single_machine=${2:-}

  local out=$BASE_DIR/stage1
  mkdir -p $out

  # Construct a one-column CSV file
  local raw_data_csv=$out/raw-data.csv
  echo 'path' > $raw_data_csv

  stage1-cachegrind $raw_dir "$single_machine" $out $raw_data_csv

  local lines_csv=$out/lines.csv

  local -a raw=()
  if test -n "$single_machine"; then
    local -a a=($raw_dir/$single_machine.*.times.csv)
    raw+=( ${a[-1]} )
    echo ${a[-1]} >> $raw_data_csv

    # They are the same, output one of them.
    cat $raw_dir/$single_machine.*.lines.csv > $lines_csv 
  else
    # Globs are in lexicographical order, which works for our dates.
    local -a a=($raw_dir/$MACHINE1.*.times.csv)
    local -a b=($raw_dir/$MACHINE2.*.times.csv)

    raw+=( ${a[-1]} ${b[-1]} )
    {
      echo ${a[-1]}
      echo ${b[-1]}
    } >> $raw_data_csv


    # Verify that the files are equal, and pass one of them.
    local -a c=($raw_dir/$MACHINE1.*.lines.csv)
    local -a d=($raw_dir/$MACHINE2.*.lines.csv)

    local left=${c[-1]}
    local right=${d[-1]}

    if ! diff $left $right; then
      die "Benchmarks were run on different files ($left != $right)"
    fi

    # They are the same, output one of them.
    cat $left > $lines_csv 
  fi

  local times_csv=$out/times.csv
  csv-concat "${raw[@]}" > $times_csv

  head $out/*
  wc -l $out/*
}

# TODO:
# - maybe rowspan for hosts: flanders/lenny
#   - does that interfere with sorting?
#
# NOTE: not bothering to make it sortable now.  Just using the CSS.

print-report() {
  local in_dir=$1

  benchmark-html-head 'OSH Parser Performance'

  cat <<EOF
  <body class="width60">
    <p id="home-link">
      <a href="/">oilshell.org</a>
    </p>
EOF

  cmark <<'EOF'
## OSH Parser Performance

We time `$sh -n $file` for various files under various shells, and repeat then
run under cachegrind for stable metrics.

Source code: [oil/benchmarks/osh-parser.sh](https://github.com/oilshell/oil/tree/master/benchmarks/osh-parser.sh)

### Summary

#### Instructions Per Line (via cachegrind)

Lower numbers are generally better, but each shell recognizes a different
language, and Oil uses a more thorough parsing algorithm.  In **thousands** of
"I refs".

EOF
  tsv2html $in_dir/cachegrind_summary.tsv

  cmark <<'EOF'

(zsh isn't measured because `zsh -n` unexpectedly forks.)

#### Average Parsing Rate, Measured on Two Machines (lines/ms)

Shell startup time is included in the elapsed time measurements, but long files
are chosen to minimize its effect.
EOF
  csv2html $in_dir/summary.csv

  cmark <<< '### Per-File Measurements'
  echo

  # Flat tables for CI
  if test -f $in_dir/times_flat.tsv; then
    cmark <<< '#### Time and Memory'
    echo

    tsv2html $in_dir/times_flat.tsv
  fi
  if test -f $in_dir/cachegrind_flat.tsv; then
    cmark <<< '#### Instruction Counts'
    echo

    tsv2html $in_dir/cachegrind_flat.tsv
  fi

  # Breakdowns for release
  if test -f $in_dir/instructions.tsv; then
    cmark <<< '#### Instructions Per Line (in thousands)'
    echo
    tsv2html $in_dir/instructions.tsv
  fi

  if test -f $in_dir/elapsed.csv; then
    cmark <<< '#### Elapsed Time (milliseconds)'
    echo
    csv2html $in_dir/elapsed.csv
  fi

  if test -f $in_dir/rate.csv; then
    cmark <<< '#### Parsing Rate (lines/ms)'
    echo
    csv2html $in_dir/rate.csv
  fi

  if test -f $in_dir/max_rss.csv; then
    cmark <<'EOF'
### Memory Usage (Max Resident Set Size in MB)

Again, Oil uses a **different algorithm** (and language) than POSIX shells.  It
builds an AST in memory rather than just validating the code line-by-line.

EOF
    csv2html $in_dir/max_rss.csv
  fi

  cmark <<EOF
### Shell and Host Details
EOF
  csv2html $in_dir/shells.csv
  csv2html $in_dir/hosts.csv

  cmark <<EOF
### Raw Data
EOF
  csv2html $in_dir/raw-data.csv

  # Only show files.html link on a single machine
  if test -f $(dirname $in_dir)/files.html; then
    cmark << 'EOF'
---
[raw files](files.html)

EOF
  fi

  cat <<EOF
  </body>
</html>
EOF
}

soil-run() {
  ### Run it on just this machine, and make a report

  rm -r -f $BASE_DIR
  mkdir -p $BASE_DIR

  local -a oil_bin=( $OSH_CPP_NINJA_BUILD )
  ninja "${oil_bin[@]}"

  local single_machine='no-host'

  local job_id
  job_id=$(benchmarks/id.sh print-job-id)

  benchmarks/id.sh shell-provenance-2 \
    $single_machine $job_id _tmp \
    bash dash bin/osh "${oil_bin[@]}"

  # TODO: measure* should use print-tasks | run-tasks
  local provenance=_tmp/provenance.txt
  local host_job_id="$single_machine.$job_id"

  measure $provenance $host_job_id '' $OSH_CPP_NINJA_BUILD

  measure-cachegrind $provenance $host_job_id '' $OSH_CPP_NINJA_BUILD

  # TODO: R can use this TSV file
  cp -v _tmp/provenance.tsv $BASE_DIR/stage1/provenance.tsv

  # Trivial concatenation for 1 machine
  stage1 '' $single_machine

  benchmarks/report.sh stage2 $BASE_DIR

  # Make _tmp/osh-parser/files.html, so index.html can potentially link to it
  find-dir-html _tmp/osh-parser files

  benchmarks/report.sh stage3 $BASE_DIR
}

"$@"

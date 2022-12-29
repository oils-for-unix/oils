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
    osh|osh_eval.*)
      extra_args='--ast-format none'
      ;;
  esac

  # exit code, time in seconds, host_hash, shell_hash, path.  \0
  # would have been nice here!
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
  local unused1=$3
  local unused2=$4
  local sh_path=$5
  local shell_hash=$6
  local script_path=$7

  echo "--- CACHEGRIND $sh_path $script_path ---"

  # NOTE: This has to match the path that the header was written to
  local times_out="$out_dir/no-host.$job_id.cachegrind.tsv"

  local cachegrind_out_dir="no-host.$job_id.cachegrind"
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
    osh|osh_eval.*)
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
    $0 cachegrind $out_dir/$cachegrind_out_path \
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

cachegrind() {
  ### Run a command under cachegrind, writing to $out_file
  local out_file=$1
  shift

  valgrind --tool=cachegrind \
    --log-file=$out_file \
    --cachegrind-out-file=/dev/null \
    -- "$@"
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
  local out_dir=${2:-$BASE_DIR/raw}
  local oil_native=${3:-$OSH_EVAL_BENCHMARK_DATA}

  # Job ID is everything up to the first dot in the filename.
  local name=$(basename $provenance)
  local prefix=${name%.provenance.txt}  # strip suffix

  local times_out="$out_dir/$prefix.times.csv"
  local lines_out="$out_dir/$prefix.lines.csv"

  mkdir -p $BASE_DIR/{tmp,raw,stage1} $out_dir

  # Files that we should measure.  Exploded into tasks.
  write-sorted-manifest '' $lines_out

  # Write Header of the CSV file that is appended to.
  benchmarks/time_.py --print-header \
    --rusage \
    --field host_name --field host_hash \
    --field shell_name --field shell_hash \
    --field path \
    > $times_out

  local tasks=$BASE_DIR/tasks.txt
  print-tasks $provenance "${SHELLS[@]}" $oil_native > $tasks

  # Run them all
  cat $tasks | xargs -n $NUM_TASK_COLS -- $0 parser-task $out_dir

  cp -v $provenance $out_dir
}

measure-cachegrind() {
  local provenance=$1
  local out_dir=${2:-$BASE_DIR/raw}
  local oil_native=${3:-$OSH_EVAL_BENCHMARK_DATA}

  # Job ID is everything up to the first dot in the filename.
  local name=$(basename $provenance)
  local prefix=${name%.provenance.txt}  # strip suffix

  local cachegrind_tsv="$out_dir/$prefix.cachegrind.tsv"
  local lines_out="$out_dir/$prefix.lines.tsv"

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
  print-tasks $provenance bash dash mksh $oil_native > $ctasks

  cat $ctasks | xargs -n $NUM_TASK_COLS -- $0 cachegrind-task $out_dir

  cp -v $provenance $out_dir
}


#
# Testing
#

# Copy data so it looks like it's from another host
fake-other-host() {
  local dir=${1:-_tmp/osh-parser/raw}
  for entry in $dir/lenny*; do
    local fake=${entry/lenny/flanders}
    #echo $entry $fake
    mv -v $entry $fake

    # The host ID isn't changed, but that's OK.
    # provencence.txt has host names.
    if test -f $fake; then
      sed -i 's/lenny/flanders/g' $fake
    fi
  done
}

#
# Data Preparation and Analysis
#

stage1-cachegrind() {
  local raw_dir=$1
  local out_dir=$2
  local raw_data_csv=$3

  local -a sorted=($raw_dir/no-host.*.cachegrind.tsv)
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

  stage1-cachegrind $raw_dir $out $raw_data_csv

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
    cmark <<< '#### Elasped Time (milliseconds)'
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

  cmark << 'EOF'
---
[raw files](files.html)

EOF

  cat <<EOF
  </body>
</html>
EOF
}

cachegrind-main() {
  ### Invoked by benchmarks/auto.sh

  local base_dir=${1:-../benchmark-data}

  local provenance
  provenance=$(benchmarks/id.sh shell-provenance no-host \
    "${OTHER_SHELLS[@]}" $OSH_EVAL_BENCHMARK_DATA)

  measure-cachegrind \
    $provenance $base_dir/osh-parser $OSH_EVAL_BENCHMARK_DATA

}

soil-shell-provenance() {
  ### Only measure shells in the Docker image

  local label=$1
  shift

  # This is a superset of shells; see filter-provenance
  # - _bin/osh isn't available in the Docker image, so use bin/osh instead

  benchmarks/id.sh shell-provenance "$label" bash dash bin/osh "$@"
}

soil-run() {
  ### Run it on just this machine, and make a report

  rm -r -f $BASE_DIR
  mkdir -p $BASE_DIR

  # TODO: could add _bin/cxx-bumpleak/osh_eval, but we would need to fix
  # $shell_name 

  local osh_eval=_bin/cxx-opt/osh_eval.stripped
  local -a oil_bin=( $osh_eval )
  ninja "${oil_bin[@]}"

  local label='no-host'

  local provenance
  provenance=$(soil-shell-provenance $label "${oil_bin[@]}")

  measure $provenance '' $osh_eval

  measure-cachegrind $provenance '' $osh_eval

  # Make it run on one machine
  stage1 '' $label

  benchmarks/report.sh stage2 $BASE_DIR
  benchmarks/report.sh stage3 $BASE_DIR

  # Index of raw files
  find-dir-html _tmp/osh-parser files
}

"$@"

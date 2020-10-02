#!/usr/bin/env bash
#
# Measure how fast the OSH parser is.
#
# Usage:
#   ./osh-parser.sh <function name>
#
# Hacky way to run it by itself:
#
#   devtools/release-native.sh make-tar
#   devtools/release-native.sh extract-for-benchmarks
#   devtools/release.sh benchmark-build
#   make  # to build _bin/osh
#   lisa:
#     benchmark/auto.sh osh-parser-quick
#   flanders:
#     TODO: fix this.  sometimes we use _bin/osh_eval.*, and sometimes the
#     ../benchmark-data/ version.
#   benchmarks/report.sh osh-parser

set -o nounset
set -o pipefail
set -o errexit

source test/common.sh  # die
source benchmarks/common.sh  # die

# TODO: The raw files should be published.  In both
# ~/git/oilshell/benchmarks-data and also in the /release/ hierarchy?
readonly BASE_DIR=_tmp/osh-parser
readonly SORTED=$BASE_DIR/tmp/sorted.txt

write-sorted-manifest() {
  local files=${1:-benchmarks/osh-parser-files.txt}
  local counts=$BASE_DIR/tmp/line-counts.txt
  local csv_out=$2

  # Remove comments and sort by line count
  grep -v '^#' $files | xargs wc -l | sort -n > $counts
    
  # Raw list of paths
  cat $counts | awk '$2 != "total" { print $2 }' > $SORTED

  # Make a CSV file from wc output
  cat $counts | awk '
      BEGIN { print "num_lines,path" }
      $2 != "total" { print $1 "," $2 }' \
      > $csv_out
}

# Calls by xargs with a task row.
parser-task() {
  local raw_dir=$1  # output
  local job_id=$2
  local host=$3
  local host_hash=$4
  local sh_path=$5
  local shell_hash=$6
  local script_path=$7

  echo "--- $sh_path $script_path ---"

  local times_out="$raw_dir/$host.$job_id.times.csv"
  local vm_out_dir="$raw_dir/$host.$job_id.virtual-memory"
  mkdir -p $vm_out_dir

  local shell_name
  shell_name=$(basename $sh_path)

  # Can't use array because of set -u bug!!!  Only fixed in bash 4.4.
  extra_args=''
  case "$shell_name" in
    osh)
      local script_name
      local vm_out_path
      script_name=$(basename $script_path)
      vm_out_path="${vm_out_dir}/${shell_name}-${shell_hash}__${script_name}.txt"
      # TODO:
      # - Add -O parse_dynamic_arith for one file?
      # - Eventually get rid of --parser-mem-dump
      extra_args="--ast-format none --parser-mem-dump $vm_out_path"

      # Should we add a field here to say it has VM stats?
      ;;

    osh_eval.*)
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

# For each shell, print 10 script paths.
print-tasks() {
  local provenance=$1

  # Add 1 field for each of 5 fields.
  cat $provenance | filter-provenance "${SHELLS[@]}" $OSH_EVAL_BENCHMARK_DATA |
  while read fields; do
    cat $SORTED | xargs -n 1 -- echo "$fields"
  done
}

readonly NUM_COLUMNS=6  # input columns: 5 from provenance, 1 for file

# output columns
readonly HEADER='status,elapsed_secs,user_secs,sys_secs,max_rss_KiB,host_name,host_hash,shell_name,shell_hash,path' 

# Figure out all tasks to run, and run them.  When called from auto.sh, $2
# should be the ../benchmarks-data repo.
measure() {
  local provenance=$1
  local raw_dir=${2:-$BASE_DIR/raw}

  # Job ID is everything up to the first dot in the filename.
  local name=$(basename $provenance)
  local prefix=${name%.provenance.txt}  # strip suffix

  local times_out="$raw_dir/$prefix.times.csv"
  local lines_out="$raw_dir/$prefix.lines.csv"

  mkdir -p $BASE_DIR/{tmp,raw,stage1} $raw_dir

  # Files that we should measure.  Exploded into tasks.
  write-sorted-manifest '' $lines_out

  # Write Header of the CSV file that is appended to.
  echo $HEADER > $times_out

  local tasks=$BASE_DIR/tasks.txt
  print-tasks $provenance > $tasks

  # Run them all
  cat $tasks | xargs -n $NUM_COLUMNS -- $0 parser-task $raw_dir

  cp -v $provenance $raw_dir
}

#
# Testing
#

# Copy data so it looks like it's from another host
fake-other-host() {
  local dir=${1:-_tmp/osh-parser/raw}
  for entry in $dir/lisa*; do
    local fake=${entry/lisa/flanders}
    #echo $entry $fake
    mv -v $entry $fake

    # The host ID isn't changed, but that's OK.
    # provencence.txt has host names.
    if test -f $fake; then
      sed -i 's/lisa/flanders/g' $fake
    fi
  done
}

#
# Data Preparation and Analysis
#

stage1() {
  local raw_dir=${1:-$BASE_DIR/raw}

  local out=$BASE_DIR/stage1
  mkdir -p $out

  local vm_csv=$out/virtual-memory.csv
  local -a x=($raw_dir/$MACHINE1.*.virtual-memory)
  local -a y=($raw_dir/$MACHINE2.*.virtual-memory)
  benchmarks/virtual_memory.py osh-parser ${x[-1]} ${y[-1]} > $vm_csv

  local times_csv=$out/times.csv
  # Globs are in lexicographical order, which works for our dates.
  local -a a=($raw_dir/$MACHINE1.*.times.csv)
  local -a b=($raw_dir/$MACHINE2.*.times.csv)

  csv-concat ${a[-1]} ${b[-1]} > $times_csv

  # Construct a one-column CSV file
  local raw_data_csv=$out/raw-data.csv
  { echo 'path'
    echo ${a[-1]}
    echo ${b[-1]}
  } > $raw_data_csv

  # Verify that the files are equal, and pass one of them.
  local lines_csv=$out/lines.csv
  local -a c=($raw_dir/$MACHINE1.*.lines.csv)
  local -a d=($raw_dir/$MACHINE2.*.lines.csv)

  local left=${c[-1]}
  local right=${d[-1]}

  if ! diff $left $right; then
    die "Benchmarks were run on different files ($left != $right)"
  fi

  # They are the same, output one of them.
  cat $left > $lines_csv 

  head $out/*
  wc -l $out/*
}

# TODO:
# - maybe rowspan for hosts: flanders/lisa
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

We run `$sh -n $file` for various files under various shells.  This means that
shell startup time is included in the elapsed time measurements, but long files
are chosen to minimize its effect.

### Average Parsing Rate, Measured on Two Machines (lines/ms)</h3>
EOF
  csv2html $in_dir/summary.csv

  cmark<<EOF
### Parse Time Breakdown by File</h3>

#### Elasped Time in milliseconds
EOF
  csv2html $in_dir/elapsed.csv

  cmark <<EOF
#### Parsing Rate in lines/millisecond
EOF
  csv2html $in_dir/rate.csv

  cmark <<EOF
### Memory Usage (Max Resident Set Size in MB)

Note that Oil uses a **different algorithm** than POSIX shells.  It builds an
AST in memory rather than just validating the code line-by-line.
EOF
  csv2html $in_dir/max_rss.csv

  cmark <<'EOF'
### Old Memory Usage Metric

Running under `osh-ovm`.  Memory usage is measured in MB (powers of 10), not
MiB (powers of 2).
EOF
  csv2html $in_dir/virtual-memory.csv

  cmark <<EOF
### Shell and Host Details
EOF
  csv2html $in_dir/shells.csv
  csv2html $in_dir/hosts.csv

  cmark <<EOF
### Raw Data
EOF
  csv2html $in_dir/raw-data.csv

  cat <<EOF
  </body>
</html>
EOF
}

time-test() {
  benchmarks/time_.py \
    --field bash --field foo.txt \
    --append --output _tmp/bench.csv \
    sleep 0.123
  cat _tmp/bench.csv
}

"$@"

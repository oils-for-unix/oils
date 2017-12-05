#!/bin/bash
#
# Measure how fast the OSH parser is.a
#
# Usage:
#   ./osh-parser.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source test/common.sh  # die

# TODO: The raw files should be published.  In both
# ~/git/oilshell/benchmarks-data and also in the /release/ hierarchy?
readonly BASE_DIR=_tmp/osh-parser
readonly SORTED=$BASE_DIR/tmp/sorted.txt

# Where we copied them from.
import-files() {
  grep -v '^#' benchmarks/osh-parser-originals.txt |
    xargs --verbose -I {} -- cp {} benchmarks/testdata
}

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
  if test "$shell_name" = 'osh'; then
    #extra_args='--ast-format none'
    local script_name
    local vm_out_path
    script_name=$(basename $script_path)
    vm_out_path="${vm_out_dir}/${shell_name}-${shell_hash}__${script_name}.txt"
    extra_args="--dump-proc-status-to $vm_out_path"

    # Should we add a field here to say it has VM stats?
  fi

  # exit code, time in seconds, host_hash, shell_hash, path.  \0
  # would have been nice here!
  benchmarks/time.py \
    --output $times_out \
    --field "$host" --field "$host_hash" \
    --field "$shell_name" --field "$shell_hash" \
    --field "$script_path" -- \
    "$sh_path" -n $extra_args "$script_path" || echo FAILED
}

# For each shell, print 10 script paths.
print-tasks() {
  local provenance=$1

  # Add 1 field for each of 5 fields.
  cat $provenance | while read fields; do
    cat $sorted | xargs -n 1 -- echo $fields
  done
}

readonly NUM_COLUMNS=6  # 5 from provenance, 1 for file

# Figure out all tasks to run, and run them.  When called from auto.sh, $2
# should be the ../benchmarks-data repo.
all() {
  local provenance=$1
  local raw_dir=${2:-$BASE_DIR/raw}

  # Job ID is everything up to the first dot in the filename.
  local name=$(basename $provenance)
  local prefix=${name%.provenance.txt}  # strip suffix

  local times_out="$raw_dir/$prefix.times.csv"
  local lines_out="$raw_dir/$prefix.lines.csv"

  mkdir -p $BASE_DIR/{tmp,raw,stage1}

  write-sorted-manifest '' $lines_out
  local sorted=$SORTED

  # Write Header of the CSV file that is appended to.
  echo 'status,elapsed_secs,host_name,host_hash,shell_name,shell_hash,path' > $times_out

  local tasks=$raw_dir/tasks.txt
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

csv-concat() {
  tools/csv_concat.py "$@"
}

stage1() {
  local raw_dir=${1:-_tmp/osh-parser/raw}
  #local raw_dir=${1:-../benchmark-data/osh-parser}

  local out=_tmp/osh-parser/stage1
  mkdir -p $out

  local vm_csv=$out/virtual-memory.csv
  local -a x=($raw_dir/flanders.*.virtual-memory)
  local -a y=($raw_dir/lisa.*.virtual-memory)
  benchmarks/virtual_memory.py osh-parser ${x[-1]} ${y[-1]} > $vm_csv

  local times_csv=$out/times.csv
  # Globs are in lexicographical order, which works for our dates.
  local -a a=($raw_dir/flanders.*.times.csv)
  local -a b=($raw_dir/lisa.*.times.csv)
  csv-concat ${a[-1]} ${b[-1]} > $times_csv

  # Construct a one-column CSV file
  local raw_data_csv=$out/raw-data.csv
  { echo 'path'
    echo ${a[-1]}
    echo ${b[-1]}
  } > $raw_data_csv

  # Verify that the files are equal, and pass one of them.
  local lines_csv=$out/lines.csv
  local -a c=($raw_dir/flanders.*.lines.csv)
  local -a d=($raw_dir/lisa.*.lines.csv)

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

stage2() {
  local out=_tmp/osh-parser/stage2
  mkdir -p $out

  benchmarks/osh-parser.R _tmp/osh-parser/stage1 $out

  tree $BASE_DIR
}

# TODO:
# - maybe rowspan for hosts: flanders/lisa
#   - does that interfere with sorting?
#
# NOTE: not bothering to make it sortable now.  Just using the CSS.

_print-report() {
  local in_dir=$1
  local base_url='../../web/table'

  cat <<EOF
<!DOCTYPE html>
<html>
  <head>
    <title>OSH Parser Performance</title>
    <script type="text/javascript" src="$base_url/table-sort.js"></script>
    <link rel="stylesheet" type="text/css" href="$base_url/table-sort.css" />

    <style>
      body {
        margin: 0 auto;
        width: 60em;
      }
      code {
        color: green;
      }
      table {
        margin-left: 3em;
        font-family: sans-serif;
      }
      td {
        padding: 8px;  /* override default of 5px */
      }
      h3, h4 {
        color: darkgreen;
      }

      /* these two tables are side by side */
      #shells, #hosts, #raw_times {
        display: inline-block;
        vertical-align: top;
      }
      #home-link {
        text-align: right;
      }

      /* columns */
      #osh-ovm, #osh-cpython {
        background-color: oldlace;
      }
      /* rows */
      .osh-row {
        background-color: oldlace;
      }

    </style>
  </head>
  <body>
    <p id="home-link">
      <a href="/">oilshell.org</a>
    </p>
    <h2>OSH Parser Performance</h2>

    <p>We run <code>\$sh -n \$file</code> for various files under various
    shells.  This means that shell startup time is included in the
    elapsed time measurements, but long files are chosen to minimize its
    effect.</p>

    <h3>Parse Time Summary</h3>
EOF
  web/table/csv2html.py $in_dir/summary.csv

  cat <<EOF
    <h3>Memory Used to Parse</h3>

    <p>For <code>osh-ovm</code>.</p>
EOF
  web/table/csv2html.py $in_dir/virtual-memory.csv

  cat <<EOF

    <h3>Shell and Host Details</h3>
EOF
  web/table/csv2html.py $in_dir/shells.csv
  web/table/csv2html.py $in_dir/hosts.csv

cat <<EOF
    <h3>Raw Data</h3>
EOF
  web/table/csv2html.py $in_dir/raw-data.csv

cat <<EOF
    <h3>Parse Time Breakdown by File</h3>

    <h4>Elasped Time in milliseconds</h4>
EOF
  web/table/csv2html.py $in_dir/elapsed.csv
  cat <<EOF

    <h4>Parsing Rate in lines/millisecond</h4>
EOF
  web/table/csv2html.py $in_dir/rate.csv
  cat <<EOF
  </body>
</html>
EOF
}

stage3() {
  local out=$BASE_DIR/index.html
  mkdir -p $(dirname $out)
  _print-report $BASE_DIR/stage2 > $out
  echo "Wrote $out"
}

report() {
  stage1
  stage2
  stage3
}

time-test() {
  benchmarks/time.py \
    --field bash --field foo.txt --output _tmp/bench.csv \
    sleep 0.123
  cat _tmp/bench.csv
}

"$@"

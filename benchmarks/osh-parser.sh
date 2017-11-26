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

import-files() {
  grep -v '^#' benchmarks/osh-parser-originals.txt |
    xargs --verbose -I {} -- cp {} benchmarks/testdata
}

# NOTE --ast-format none eliminates print time!  That is more than
# half of it!  ( 60 seconds with serialization, 29 seconds without.)
# TODO: That is the only difference... hm.
#
# TODO:
# - Have OSH --parse-and-dump-path
#   - it can dump /proc/self/meminfo

sh-one() {
  local append_out=$1
  local vm_out_dir=$2
  local sh_path=$3
  local host_name=$4
  local host_hash=$5
  local shell_hash=$6
  local path=$7
  echo "--- $sh_path $path ---"

  local shell_name
  shell_name=$(basename $sh_path)

  # Can't use array because of set -u bug!!!  Only fixed in bash
  # 4.4.
  extra_args=''
  if test "$shell_name" = 'osh'; then
    #extra_args='--ast-format none'
    local script_name
    local vm_out_path
    script_name=$(basename $path)
    vm_out_path="${vm_out_dir}/${shell_name}-${shell_hash}__${script_name}.txt"
    extra_args="--dump-proc-status-to $vm_out_path"
    # And then add that as --field?
    # This adds 0.01 seconds?
    # or shell_hash
    # Then you need a Python or R script to make a CSV file out of VmPeak VmRSS
    # etc.
  fi

  # exit code, time in seconds, host_hash, shell_hash, path.  \0
  # would have been nice here!
  benchmarks/time.py \
    --output $append_out \
    --field "$host_name" --field "$host_hash" \
    --field "$shell_name" --field "$shell_hash" \
    --field "$path" -- \
    "$sh_path" -n $extra_args "$path" || echo FAILED
}

import-files() {
  grep -v '^#' benchmarks/osh-parser-originals.txt |
    xargs --verbose -I {} -- cp {} benchmarks/testdata
}

write-sorted-manifest() {
  local files=${1:-benchmarks/osh-parser-files.txt}
  local counts=$BASE_DIR/raw/line-counts.txt
  local csv=$2

  # Remove comments and sort by line count
  grep -v '^#' $files | xargs wc -l | sort -n > $counts
    
  # Raw list of paths
  cat $counts | awk '$2 != "total" { print $2 }' > $SORTED

  # Make a LINES_CSV from wc output
  cat $counts | awk '
      BEGIN { print "num_lines,path" }
      $2 != "total" { print $1 "," $2 }' \
      > $csv

  cat $SORTED
  echo ---
  cat $csv
}

# runtime_id, host_hash, toolchain_id (which sometimes you don't know)

run() {
  local preview=${1:-}
  local host
  host=$(hostname)

  local job_id
  job_id="$host.$(date +%Y-%m-%d__%H-%M-%S)"

  local out_dir='../benchmark-data/osh-parser'
  local times_out="$out_dir/$job_id.times.csv"
  local lines_out="$out_dir/$job_id.lines.csv"
  local vm_out_dir="$out_dir/$job_id.virtual-memory"

  mkdir -p \
    $(dirname $times_out) \
    $vm_out_dir \
    $BASE_DIR/{tmp,raw,stage1,www}

  write-sorted-manifest '' $lines_out
  local sorted=$SORTED

  # Write Header of the CSV file that is appended to.
  echo 'status,elapsed_secs,host_name,host_hash,shell_name,shell_hash,path' \
    > $times_out

  local tmp_dir=_tmp/host-id/$host
  benchmarks/id.sh dump-host-id $tmp_dir

  local host_hash
  host_hash=$(benchmarks/id.sh publish-host-id $tmp_dir)
  echo $host $host_hash

  local shell_hash

  #for sh_path in bash dash mksh zsh; do
  for sh_path in bash dash mksh zsh bin/osh _bin/osh; do
    # There will be two different OSH
    local name=$(basename $sh_path)

    tmp_dir=_tmp/shell-id/$name
    benchmarks/id.sh dump-shell-id $sh_path $tmp_dir

    shell_hash=$(benchmarks/id.sh publish-shell-id $tmp_dir)

    echo "$sh_path ID: $shell_hash"

    if ! test -n "$preview"; then
      # 20ms for ltmain.sh; 34ms for configure
      cat $sorted | xargs -n 1 -- $0 \
        sh-one $times_out $vm_out_dir $sh_path $host $host_hash $shell_hash || true
    fi
  done

  cat $times_out
  echo "Wrote $times_out, $lines_out, and $vm_out_dir/"
}

#
# Data Preparation and Analysis
#

csv-concat() {
  tools/csv_concat.py "$@"
}

stage1() {
  local out=_tmp/osh-parser/stage1
  mkdir -p $out

  local vm_csv=$out/virtual-memory.csv
  local -a x=(../benchmark-data/osh-parser/flanders.*.virtual-memory)
  local -a y=(../benchmark-data/osh-parser/lisa.*.virtual-memory)
  benchmarks/virtual_memory.py osh-parser ${x[-1]} ${y[-1]} > $vm_csv

  local times_csv=$out/times.csv
  # Globs are in lexicographical order, which works for our dates.
  local -a a=(../benchmark-data/osh-parser/flanders.*.times.csv)
  local -a b=(../benchmark-data/osh-parser/lisa.*.times.csv)
  csv-concat ${a[-1]} ${b[-1]} > $times_csv

  # Construct a one-column CSV file
  local raw_data_csv=$out/raw-data.csv
  { echo 'path'
    echo ${a[-1]}
    echo ${b[-1]}
  } > $raw_data_csv

  # Verify that the files are equal, and pass one of them.
  local lines_csv=$out/lines.csv
  local -a c=(../benchmark-data/osh-parser/flanders.*.lines.csv)
  local -a d=(../benchmark-data/osh-parser/lisa.*.lines.csv)

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

_banner() {
  echo -----
  echo "$@"
  echo -----
}

# Run the whole benchmark from a clean git checkout.
#
# Similar to scripts/release.sh build-and-test.
auto() {
  test/spec.sh install-shells

  # Technically we need build-essential too?
  sudo apt install python-dev

  build/dev.sh all
  build/codegen.sh lexer

  _banner 'OSH dev build'
  bin/osh -c 'echo OSH dev build'

  build/prepare.sh configure
  build/prepare.sh build-python

  make _bin/oil.ovm
  # This does what 'install' does.
  scripts/run.sh make-bin-links

  _banner 'OSH production build'

  _bin/osh -c 'echo OSH production build'

  run  # make observations

  # Then summarize report can be done on a central machine?
}

time-test() {
  benchmarks/time.py \
    --field bash --field foo.txt --output _tmp/bench.csv \
    sleep 0.123
  cat _tmp/bench.csv
}

"$@"

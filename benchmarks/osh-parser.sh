#!/bin/bash
#
# Measure how fast the OSH parser is.a
#
# Usage:
#   ./osh-parser.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

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
  local sh_path=$2
  local host_name=$3
  local host_hash=$4
  local shell_hash=$5
  local path=$6
  echo "--- $sh_path $path ---"

  local shell_name
  shell_name=$(basename $sh_path)

  # Can't use array because of set -u bug!!!  Only fixed in bash
  # 4.4.
  extra_args=''
  if test "$shell_name" = 'osh'; then
    extra_args='--ast-format none'
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

  local out_dir='../benchmark-data/osh-parser/'
  local out="$out_dir/$job_id.times.csv"
  local lines_out="$out_dir/$job_id.lines.csv"

  mkdir -p \
    $(dirname $out) \
    $BASE_DIR/{tmp,raw,stage1,www}

  write-sorted-manifest '' $lines_out
  local sorted=$SORTED

  # Write Header of the CSV file that is appended to.
  echo 'status,elapsed_secs,host_name,host_hash,shell_name,shell_hash,path' > $out

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

    # TODO: Shell ID should be separate columns?
    # It's really shell_version_id?

    if ! test -n "$preview"; then
      # 20ms for ltmain.sh; 34ms for configure
      cat $sorted | xargs -n 1 -- $0 \
        sh-one $out $sh_path $host $host_hash $shell_hash || true
    fi
  done

  cat $out
  echo "Wrote $out"
}

# TODO: 
summarize() {
  local out=_tmp/osh-parser/stage1
  mkdir -p $out

  # Globs are in lexicographical order, which works for our dates.
  local -a m1=(../benchmark-data/osh-parser/flanders.*.times.csv)
  local -a m2=(../benchmark-data/osh-parser/lisa.*.times.csv)

  # The last one
  local -a latest=(${m1[-1]} ${m2[-1]})

  benchmarks/osh-parser.R $out "${latest[@]}"

  tree $BASE_DIR
}

# TODO:
# - maybe rowspan for hosts: flanders/lisa
#   - does that interfere with sorting?
#
# NOTE: not bothering to make it sortable now.  Just using the CSS.

_print-report() {
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

    <h3>Summary</h3>

EOF
  web/table/csv2html.py $BASE_DIR/stage1/summary.csv
  cat <<EOF

    <h3>Shell and Host Details</h3>
EOF
  web/table/csv2html.py $BASE_DIR/stage1/shells.csv
  web/table/csv2html.py $BASE_DIR/stage1/hosts.csv

cat <<EOF
    <h3>Raw Timing Data</h3>
EOF
  web/table/csv2html.py $BASE_DIR/stage1/raw_times.csv
cat <<EOF

    <h3>Per-File Breakdown</h3>

    <h4>Elasped Time in milliseconds</h4>
EOF
  web/table/csv2html.py $BASE_DIR/stage1/elapsed.csv
  cat <<EOF

    <h4>Parsing Rate in lines/millisecond</h4>
EOF
  web/table/csv2html.py $BASE_DIR/stage1/rate.csv
  cat <<EOF
  </body>
</html>
EOF
}

report() {
  local out=$BASE_DIR/index.html
  mkdir -p $(dirname $out)
  _print-report > $out
  echo "Wrote $out"
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

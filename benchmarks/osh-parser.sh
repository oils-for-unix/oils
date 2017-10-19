#!/bin/bash
#
# Usage:
#   ./osh-parser.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

readonly BASE_DIR=_tmp/osh-parser
readonly SORTED=$BASE_DIR/input/sorted.txt
readonly TIMES_CSV=$BASE_DIR/raw/times.csv
readonly LINES_CSV=$BASE_DIR/raw/line-counts.csv

# NOTE --ast-format none eliminates print time!  That is more than half of it!
# ( 60 seconds with serialization, 29 seconds without.)
#
# TODO: Lines per second is about 1700
# Run each file twice and compare timing?

# TODO: Use the compiled version without our Python, not system Python!
# Compilation flags are different.
# - Well maybe we want both.

osh-parse-one() {
  local path=$1
  echo "--- $path ---"

  TIMEFORMAT="%R osh $path"  # elapsed time

  benchmarks/time.py \
    --output $TIMES_CSV \
    --field osh --field "$path" -- \
    bin/osh -n --ast-format none $path
}

sh-one() {
  local sh=$1
  local path=$2
  echo "--- $sh -n $path ---"

  # Since we're running benchmarks serially, just append to the same file.
  TIMEFORMAT="%R $sh $path"  # elapsed time

  # exit code, time in seconds, sh, path.  \0 would have been nice here!
  benchmarks/time.py \
    --output $TIMES_CSV \
    --field "$sh" --field "$path" -- \
    $sh -n $path || echo FAILED
}

write-sorted-manifest() {
  local files=${1:-benchmarks/osh-parser-files.txt}
  local counts=$BASE_DIR/raw/line-counts.txt
  local csv=$LINES_CSV

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

run() {
  mkdir -p $BASE_DIR/{input,raw,stage1,www}

  write-sorted-manifest
  local sorted=$SORTED

  # Header 
  echo 'status,elapsed_secs,shell,path' > $TIMES_CSV

  # 20ms for ltmain.sh; 34ms for configure
  cat $sorted | xargs -n 1 $0 sh-one bash || true

  # Wow dash is a lot faster, 5 ms / 6 ms.  It even gives one syntax error.
  cat $sorted | xargs -n 1 $0 sh-one dash || true

  # mksh is in between: 11 / 23 ms.
  cat $sorted | xargs -n 1 $0 sh-one mksh || true

  # zsh really slow: 45 ms and 124 ms.
  cat $sorted | xargs -n 1 $0 sh-one zsh || true

  # 4 s and 15 s.  So 1000x speedup would be sufficient, not 10,000x!
  time cat $sorted | xargs -n 1 $0 osh-parse-one

  cat $TIMES_CSV
}

summarize() {
  local out=_tmp/osh-parser/stage1
  mkdir -p $out
  benchmarks/osh-parser.R $LINES_CSV $TIMES_CSV $out

  tree $BASE_DIR
}

_print-report() {
  local base_url='../../../web/table'

  cat <<EOF
<!DOCTYPE html>
<html>
  <head>
    <title>OSH Parser Benchmark</title>
    <script type="text/javascript" src="$base_url/table-sort.js"></script>
    <link rel="stylesheet" type="text/css" href="$base_url/table-sort.css" />

    <style>
      td { text-align: right; }
      body {
        margin: 0 auto;
        width: 60em;
      }
      code { color: green; }
    </style>
  </head>
  <body>
    <h2>OSH Parser Benchmark</h2>

    <p>We run <code>\$sh -n \$file</code> for various files under various
    shells.  This means that shell startup time is included in the
    elapsed time measurements, but long files are chosen to minimize its
    effect.</p>

    <h3>Elasped Time by File and Shell (milliseconds)</h3>

    <table id="elapsed">
EOF
  web/table/csv_to_html.py < $BASE_DIR/stage1/elapsed.csv
  cat <<EOF
    </table>

    <h3>Parsing Rate by File and Shell (lines/millisecond)</h3>

    <table id="rate">
EOF
  web/table/csv_to_html.py < $BASE_DIR/stage1/rate.csv
  cat <<EOF
    </table>

    <h3>Summary</h3>

    <table id="rate-summary">
EOF
  web/table/csv_to_html.py < $BASE_DIR/stage1/rate_summary.csv
  cat <<EOF
    </table>
  </body>
</html>
EOF
}

report() {
  local out=$BASE_DIR/www/summary.html
  _print-report > $out
  echo "Wrote $out"
}

# TODO:
# - Parse the test file -> csv.  Have to get rid of syntax errors?
#   - I really want --output.  
#   - benchmarks/time.py is probably appropriate now.
# - reshape, total, and compute lines/sec
#   - that is really a job for R
#   - maybe you need awk to massage wc output into LINES_CSV
# - csv_to_html.py
# - Then a shell script here to put CSS and JS around it.
#   - wild-static
# - Publish to release/0.2.0/benchmarks/MACHINE/wild/

time-test() {
  benchmarks/time.py \
    --field bash --field foo.txt --output _tmp/bench.csv \
    sleep 0.123
  cat _tmp/bench.csv
}

"$@"

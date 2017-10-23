#!/bin/bash
#
# Measure how fast the OSH parser is.a
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
# TODO:
# - Have OSH --parse-and-dump-path
#   - it can dump /proc/self/meminfo

osh-parse-one() {
  local append_out=$1
  local path=$2
  echo "--- $path ---"

  benchmarks/time.py \
    --output $append_out \
    --field osh --field "$path" -- \
    bin/osh -n --ast-format none $path
}

sh-one() {
  local append_out=$1
  local sh=$2
  local path=$3
  echo "--- $sh -n $path ---"

  # Since we're running benchmarks serially, just append to the same file.
  TIMEFORMAT="%R $sh $path"  # elapsed time

  # exit code, time in seconds, sh, path.  \0 would have been nice here!
  benchmarks/time.py \
    --output $append_out \
    --field "$sh" --field "$path" -- \
    $sh -n $path || echo FAILED
}

import-files() {
  grep -v '^#' benchmarks/osh-parser-originals.txt |
    xargs --verbose -I {} -- cp {} benchmarks/testdata
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

  # This file is appended to
  local out=$TIMES_CSV

  # Header 
  echo 'status,elapsed_secs,shell,path' > $TIMES_CSV

  # 20ms for ltmain.sh; 34ms for configure
  cat $sorted | xargs -n 1 $0 sh-one $out bash || true

  # Wow dash is a lot faster, 5 ms / 6 ms.  It even gives one syntax error.
  cat $sorted | xargs -n 1 $0 sh-one $out dash || true

  # mksh is in between: 11 / 23 ms.
  cat $sorted | xargs -n 1 $0 sh-one $out mksh || true

  # zsh really slow: 45 ms and 124 ms.
  cat $sorted | xargs -n 1 $0 sh-one $out zsh || true

  # TODO:
  # - Run OSH under OVM
  # - Run OSH compiled with OPy
  # Maybe these are gradual release upgrades?
  return

  # 4 s and 15 s.  So 1000x speedup would be sufficient, not 10,000x!
  time cat $sorted | xargs -n 1 $0 osh-parse-one $out

  cat $TIMES_CSV
  echo $TIMES_CSV
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

#
# Record Provenance: Code, Data, Env
#

# - code: We will run against different shells (bash, dash, OSH).  The OSH
# code will improve over time
# - env: we test it on different machines (machine architecture, OS, distro,
# etc.)
# - data ID: (name, num_lines) is sufficient I think.  Don't bother with hash.
#   - or does (name, hash) make sense?

# TODO:
# - add code_id to CSV (time.py), and code-id.txt?

code-id() {
  # columns for osh:
  # vm,compiler

  # columns for other:
  # --version

  # osh --version?
  # git branch, etc.?

  # running system python, or OVM?
  echo TODO
}

# Just hash the files?
data-id() {
  echo TODO
}

# Events that will change the env for a given machine:
# - kernel upgrade
# - distro upgrade

env-id() {
  local out_dir=${1:-_tmp/env-id-$(hostname)}

  mkdir -p $out_dir

  hostname > $out_dir/hostname.txt

  # does it make sense to do individual fields like -m?
  # avoid parsing?
  # We care about the kernel and the CPU architecture.
  # There is a lot of redundant information there.
  uname -m > $out_dir/machine.txt
  # machine
  { uname --kernel-release 
    uname --kernel-version
  } > $out_dir/kernel.txt

  cat /proc/cpuinfo > $out_dir/cpuinfo.txt

  # mem info doesn't make a difference?  I guess it's just nice to check that
  # it's not swapping.  But shouldn't be part of the hash.
  cat /proc/meminfo > $out_dir/meminfo.txt

  cat /etc/lsb-release > $out_dir/lsb-release.txt
  cat /etc/debian_version > $out_dir/debian_version.txt

  head $out_dir/*

  # Now should I create a hash from this?
  # like x86_64__linux__distro?
  # There is already concept of the triple?
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

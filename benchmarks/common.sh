#!/bin/bash
#
# Common functions for benchmarks.
#

# What binary the benchmarks will run.
readonly OSH_OVM=${OSH_OVM:-$PWD/_bin/osh}

# NOTE: This is in {build,test}/common.sh too.
die() {
  echo "FATAL: $@" 1>&2
  exit 1
}

log() {
  echo "$@" 1>&2
}

csv-concat() { tools/csv_concat.py "$@"; }

# TSV and CSV concatenation are actually the same.  Just use the same script.
tsv-concat() { tools/csv_concat.py "$@"; }

# For compatibility, if cell starts with 'osh', apply the 'special' CSS class.
csv2html() {
  web/table/csv2html.py --css-class-pattern 'special ^osh' "$@";
}

tsv2html() {
  web/table/csv2html.py --tsv "$@";
}

# Need an absolute path here.
readonly _time_tool=$PWD/benchmarks/time.py 
time-tsv() { $_time_tool --tsv "$@"; }

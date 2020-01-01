#!/bin/bash
#
# Common functions for benchmarks.
#

# What binary the benchmarks will run.  NOTE: should be RELATIVE, because
# there's a hack to make it absolute in benchmarks/osh-runtime.sh.  TODO:
# consolidate with OSH_OVM in test/common.sh.
readonly OSH_OVM=${OSH_OVM:-_bin/osh}

readonly MACHINE1=flanders
readonly MACHINE2=lisa

#readonly MACHINE1=broome
#readonly MACHINE2=spring

# NOTE: This is in {build,test}/common.sh too.
die() {
  echo "FATAL: $@" 1>&2
  exit 1
}

log() {
  echo "$@" 1>&2
}

csv-concat() { devtools/csv_concat.py "$@"; }

# TSV and CSV concatenation are actually the same.  Just use the same script.
tsv-concat() { devtools/csv_concat.py "$@"; }

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

# also in metrics/source-code.sh
hist() { sort | uniq -c | sort -n; }

html-head() {
  PYTHONPATH=. doctools/html_head.py "$@"
}

benchmark-html-head() {
  local title="$1"

  local base_url='../../web'

  html-head --title "$title" \
    "$base_url/table/table-sort.js" \
    "$base_url/table/table-sort.css" \
    "$base_url/base.css"\
    "$base_url/benchmarks.css"
}

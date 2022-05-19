#!/usr/bin/env bash
#
# Common functions for benchmarks.
#

#readonly MACHINE1=flanders
#readonly MACHINE2=lenny

readonly MACHINE1=broome
readonly MACHINE2=lenny

OIL_VERSION=$(head -n 1 oil-version.txt)
readonly BENCHMARK_DATA_OIL_NATIVE=$PWD/../benchmark-data/src/oil-native-$OIL_VERSION
readonly OSH_EVAL_BENCHMARK_DATA=$BENCHMARK_DATA_OIL_NATIVE/_bin/cxx-opt-sh/osh_eval.stripped

#
# Binaries we want to test, which can be overridden
#

OSH_OVM=${OSH_OVM:-_bin/osh}  # This is overridden by devtools/release.sh.
OIL_NATIVE=${OIL_NATIVE:-$OSH_EVAL_BENCHMARK_DATA}

readonly OTHER_SHELLS=( bash dash mksh zsh )
readonly SHELLS=( ${OTHER_SHELLS[@]} bin/osh $OSH_OVM )

# NOTE: This is in {build,test}/common.sh too.
die() {
  echo "FATAL: $@" 1>&2
  exit 1
}

log() {
  echo "$@" 1>&2
}

cmark() {
  # A filter to making reports
  PYTHONPATH=. doctools/cmark.py "$@"
}

csv-concat() { devtools/csv_concat.py "$@"; }

# TSV and CSV concatenation are actually the same.  Just use the same script.
tsv-concat() { devtools/csv_concat.py "$@"; }

# For compatibility, if cell starts with 'osh', apply the 'special' CSS class.
csv2html() {
  web/table/csv2html.py --css-class-pattern 'special ^osh' "$@"
}

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

filter-provenance() {
  # create a regex bash|dash
  local pat=$(echo "$@" | sed 's/ /|/g')

  # Anchor it at the end only.  For _bin/cxx-opt/osh_eval.stripped and the
  # ../benchmark-data one.
  pat="($pat)\$"

  # 4th column is the shell
  awk -v pat="$pat" '$4 ~ pat { print }'
}

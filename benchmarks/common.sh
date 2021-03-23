#!/usr/bin/env bash
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

# Notes:
# - $OSH_OVM is set by devtools/release.sh to the RELATIVE path of the
#   tar-built one.  Instead of the default of $PWD/_bin/osh.
# - These are NOT the versions of bash/dash/etc. in _tmp/spec-bin!  I
#   guess we should test distro-provided binaries.

readonly SHELLS=( bash dash mksh zsh bin/osh $OSH_OVM )

# for valgrind
readonly NATIVE_SHELLS=( bash dash mksh zsh $OSH_OVM )

readonly OIL_VERSION=$(head -n 1 oil-version.txt)

# Needed to run on flanders
readonly root=$PWD/../benchmark-data/src/oil-native-$OIL_VERSION
readonly OSH_EVAL_BENCHMARK_DATA=$root/_bin/osh_eval.opt.stripped


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
  web/table/csv2html.py --css-class-pattern 'special ^osh' "$@";
}

tsv2html() {
  web/table/csv2html.py --tsv "$@";
}

# Need an absolute path here.
readonly _time_tool=$PWD/benchmarks/time_.py 
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

filter-provenance() {
  # create a regex bash|dash
  local pat=$(echo "$@" | sed 's/ /|/g')

  # Anchor it at the end only.  For _bin/osh_eval.opt.stripped and the
  # ../benchmark-data one.
  pat="($pat)$"

  # 4th column is the shell
  awk -v pat="$pat" '$4 ~ pat { print }'
}

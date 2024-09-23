#!/usr/bin/env bash
#
# Common functions for benchmarks.
#

# Include guard.
test -n "${__BENCHMARKS_COMMON_SH:-}" && return
readonly __BENCHMARKS_COMMON_SH=1

#readonly MACHINE1=flanders
#readonly MACHINE2=lenny

# 2023-11-29: MACHINE1=lenny MACHINE2=hoover

# 2024-08-23: MACHINE1=hoover MACHINE2=mercer
# Because we gained a Souffle dependency, which requires C++17.  And the base
# image on lenny doesn't support C++17.

readonly MACHINE1=hoover
readonly MACHINE2=mercer

OIL_VERSION=$(head -n 1 oil-version.txt)

# Used by devtools/release.sh
readonly BENCHMARK_DATA_OILS=$PWD/../benchmark-data/src/oils-for-unix-$OIL_VERSION

readonly OSH_CPP_NINJA_BUILD=_bin/cxx-opt/osh
readonly OSH_SOUFFLE_CPP_NINJA_BUILD=_bin/cxx-opt/mycpp-souffle/osh

readonly OSH_CPP_SH_BUILD=_bin/cxx-opt-sh/osh
readonly OSH_SOUFFLE_CPP_SH_BUILD=_bin/cxx-opt-sh/mycpp-souffle/osh
readonly YSH_CPP_SH_BUILD=_bin/cxx-opt-sh/ysh

readonly OSH_CPP_BENCHMARK_DATA=$BENCHMARK_DATA_OILS/$OSH_CPP_SH_BUILD
readonly OSH_SOUFFLE_CPP_BENCHMARK_DATA=$BENCHMARK_DATA_OILS/$OSH_SOUFFLE_CPP_SH_BUILD
readonly YSH_CPP_BENCHMARK_DATA=$BENCHMARK_DATA_OILS/$YSH_CPP_SH_BUILD

#
# Binaries we want to test, which can be overridden
#

OSH_OVM=${OSH_OVM:-_bin/osh}  # This is overridden by devtools/release.sh.

readonly OTHER_SHELLS=( bash dash mksh zsh )
readonly SHELLS=( ${OTHER_SHELLS[@]} bin/osh $OSH_OVM )

# Passed to awk in filter-provenance.  TODO: This could be a parameter
# Awk wants this to be \\. ?  Probably should stop using Awk.
readonly OSH_CPP_REGEX='_bin/.*/osh'

log() {
  echo "$@" >&2
}

# NOTE: This is in {build,test}/common.sh too.
die() {
  log "$0: fatal: $@"
  exit 1
}


cmark() {
  # A filter to making reports
  PYTHONPATH=. doctools/cmark.py "$@"
}

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

  # Anchor it at the end only.  For _bin/cxx-opt/oils-for-unix.stripped and the
  # ../benchmark-data one.
  pat="($pat)\$"

  # 4th column is the shell
  awk -v pat="$pat" '$4 ~ pat { print }'
}

maybe-tree() {
  ### Run tree command if it's installed
  if command -v tree; then
    tree "$@"
  fi
}

#!/usr/bin/env bash
#
# Common functions for benchmarks.
#

# Include guard.
test -n "${__BENCHMARKS_COMMON_SH:-}" && return
readonly __BENCHMARKS_COMMON_SH=1

# 2024-12: Moved back to local machines

readonly MACHINE1=hoover
readonly MACHINE2=lenny
#readonly MACHINE2=mercer

OILS_VERSION=$(head -n 1 oils-version.txt)

readonly _NINJA_BUILD=_bin/cxx-opt
readonly OSH_CPP_NINJA=$_NINJA_BUILD/osh
readonly OSH_SOUFFLE_CPP_NINJA=$_NINJA_BUILD/mycpp-nosouffle/osh

# Used by devtools/release.sh
readonly BENCHMARK_DATA_OILS=$PWD/../benchmark-data/src/oils-for-unix-$OILS_VERSION
readonly _SH_BUILD=_bin/cxx-opt-sh

readonly OSH_CPP_SOIL=$_SH_BUILD/osh
readonly OSH_SOUFFLE_CPP_SOIL=$_SH_BUILD/mycpp-nosouffle/osh

readonly OSH_CPP_TWO=$BENCHMARK_DATA_OILS/$OSH_CPP_SOIL
readonly OSH_SOUFFLE_CPP_TWO=$BENCHMARK_DATA_OILS/$OSH_SOUFFLE_CPP_SOIL

readonly YSH_CPP_SOIL=$_SH_BUILD/ysh
readonly YSH_CPP_TWO=$BENCHMARK_DATA_OILS/$YSH_CPP_SOIL

# We always build from the tarball
readonly OSH_STATIC_SOIL=$_SH_BUILD/osh-static
readonly OSH_STATIC_TWO=$BENCHMARK_DATA_OILS/$OSH_STATIC_SOIL


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

# Used in benchmarks/gc and benchmarks/compute
banner() {
  echo -----
  echo "$@"
}

cmark() {
  # A filter to making reports
  PYTHONPATH=.:vendor doctools/cmark.py "$@"
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
    "$base_url/base.css" \
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

#!/usr/bin/env bash
#
# A pure string-processing benchmark extracted from bash-completion.
#
# Note: most stuff moved to benchmarks/compute.
#
# Usage:
#   benchmarks/parse-help.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

readonly DATA_DIR='benchmarks/parse-help'
readonly EXCERPT=benchmarks/parse-help/excerpt.sh

# TODO: Check these in to testdata/parse-help
collect() {
  mkdir -p $DATA_DIR

  ls --help > $DATA_DIR/ls.txt
  ~/.local/bin/mypy --help > $DATA_DIR/mypy.txt

  wc -l $DATA_DIR/*
}

shorten() {
  egrep '^[ ]+-' $DATA_DIR/ls.txt | head -n 2 | tee $DATA_DIR/ls-short.txt
}

TIMEFORMAT='%U'

# Geez:
#        ls     mypy
# bash   25ms   25ms
# OSH   600ms  900ms   There is a lot of variance here too.

# Well I guess that is 25x slower?  It's a computationally expensive thing.
# Oh part of this is because printf is not a builtin!  Doh.
#
# TODO
# - count the number of printf invocations.  But you have to do it recursively!
# - Turn this into a proper benchmark with an HTML page.

one() {
  local sh='bin/osh'
  local cmd='ls-short'
  export PS4='+[${LINENO}:${FUNCNAME[0]}] '
  time cat $DATA_DIR/$cmd.txt | $sh -x $EXCERPT _parse_help -
}

compare-one() {
  local cmd='ls-short'
  time cat $DATA_DIR/$cmd.txt | bin/osh $EXCERPT _parse_help -
  echo ---
  time cat $DATA_DIR/$cmd.txt | bash $EXCERPT _parse_help -
}

"$@"

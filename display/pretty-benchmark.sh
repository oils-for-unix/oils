#!/usr/bin/env bash
#
# Usage:
#   data_lang/pretty-benchmark.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

# Only show real time
TIMEFORMAT='%R'
# User time is also interesting
# TIMEFORMAT='%U'

# It takes much longer to print than to parse.
#
# Output example:
#
# benchmarks/testdata/configure-coreutils - parsing only, then parsing and printing
# AST not printed.
# 0.129
# 
# 108811544  # <-- This is 109 MB of output text!
# 3.679

# 2024-11
# 74292325  # 74 MB
# 2.668

compare() {
  local osh=_bin/cxx-opt/osh
  ninja $osh

  for file in benchmarks/testdata/conf*; do
    echo ---
    echo "$file - parsing only, then parsing and printing"

    # Don't print at all.  configure-coreutils is 136 ms.
    time $osh --ast-format none --tool syntax-tree $file
    echo

    # Print the whole thing
    time $osh --ast-format text --tool syntax-tree $file | wc --bytes
    echo

    # Print abbreviated
    time $osh --tool syntax-tree $file | wc --bytes
    echo

  done
}

test-abbrev() {
  local osh=_bin/cxx-opt/osh
  ninja $osh

  local file=benchmarks/testdata/configure-coreutils


  time $osh --ast-format text --tool syntax-tree $file > _tmp/pretty-text-1.txt
  time $osh --ast-format text --tool syntax-tree $file > _tmp/pretty-text-2.txt

  # object IDs are not the same!
  time $osh --tool syntax-tree $file > _tmp/pretty-abbrev.txt

  wc --bytes _tmp/pretty-*
}

float-demo() {
  ### Test of tabular floats - not a test or a benchmark right now

  # Note: this could change if we change how floats are printed, e.g. strtof
  # vs. strtod.

  local ysh=_bin/cxx-asan/ysh
  ninja $ysh

  #ysh=bin/ysh

  $ysh -c '
var L = []
for i in (1 .. 200) {
  call L->append(i/30)
}
= L
'
}

"$@"

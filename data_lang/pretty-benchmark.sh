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

compare() {
  local osh=_bin/cxx-opt/osh
  ninja $osh

  for file in benchmarks/testdata/*; do
    echo ---
    echo "$file - parsing only, then parsing and printing"

    # Don't print at all.  configure-coreutils is 136 ms.
    time $osh --ast-format none --tool syntax-tree $file
    echo

    # Print the whole thing
    time $osh --ast-format text --tool syntax-tree $file | wc --bytes
    echo

  done
}

float-demo() {
  ### Test of tabular floats - not a test or a benchmark right now

  # Note: this could change if we change how floats are printed, e.g. strtof
  # vs. strtod.

  bin/ysh -c '
var L = []
for i in (1 .. 200) {
  call L->append(i/3)
}
= L
'
}

"$@"

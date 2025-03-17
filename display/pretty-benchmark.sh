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

# NEW Wadler printer!


compare() {
  local osh=_bin/cxx-opt/osh
  ninja $osh

  #for file in benchmarks/testdata/conf*; do
  for file in benchmarks/testdata/configure; do
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

gc-stats() {
  local osh=_bin/cxx-opt/osh
  #local osh=_bin/cxx-asan/osh
  ninja $osh

  # We should be doing some big GCs here
  export _OILS_GC_VERBOSE=1

  # 41 KB file
  for file in benchmarks/testdata/functions; do
  # 615K file
  #for file in benchmarks/testdata/configure; do

  # THIS FILE MAKES MY COMPUTER LOCK UP SOMETIMES!
  # 1.7 MB file
  #for file in benchmarks/testdata/configure-coreutils; do

    local fmt=__perf
    echo "___ parsing and pretty printing $file"
    time OILS_GC_STATS=1 $osh --ast-format $fmt --tool syntax-tree $file | wc --bytes
    echo

    continue

    # even after adding GC
    # - max RSS is 878 MB, on configure
    #   - other the other hand, the output is just 30 MB (30,370,809 bytes)
    # - max RSS is 2,386 MB, on configure-coreutils
    /usr/bin/time --format '*** elapsed %e, max RSS %M' -- \
      $osh --ast-format $fmt --tool syntax-tree $file | wc --bytes
    echo

    echo "OLD printer"
    # Compare against OLD printer
    time OILS_GC_STATS=1 osh --ast-format text --tool syntax-tree $file | wc --bytes

    continue
    echo ---

    # 585K objects allocated, 16 MB
    echo "$file - parsing only"
    time OILS_GC_STATS=1 $osh --ast-format none --tool syntax-tree $file
    echo

    # 14M allocated, 450 MB!  Geez!
    echo "$file - parsing, pretty print abbreviated"
    time OILS_GC_STATS=1 $osh --tool syntax-tree $file | wc --bytes
    echo

    # 31 M allocated, 1 GB!   Gah
    echo "$file - parsing, pretty print full"
    time OILS_GC_STATS=1 $osh --ast-format text --tool syntax-tree $file | wc --bytes
    echo

  done
}

readonly -a FILES=(
  benchmarks/testdata/{functions,configure}

  # This file is known to lock up my Debian machine!  It seems to go into a
  # swap loop.
  # configure-coreutils
)

count-small() {
  # Python
  bin/osh --ast-format __perf --tool syntax-tree -c 'echo hi'
  return

  local osh=_bin/cxx-opt/osh
  #local osh=_bin/cxx-dbg/osh
  ninja $osh

  /usr/bin/time --format '*** elapsed %e, max RSS %M' -- \
    $osh --ast-format __perf --tool syntax-tree -c 'echo hi'
}

counters() {
  local osh=_bin/cxx-opt/osh
  #local osh=_bin/cxx-dbg/osh
  ninja $osh

  #export OILS_GC_STATS=1

  for file in "${FILES[@]}"; do
    echo "=== parsing and pretty printing $file"
    echo

    /usr/bin/time --format '*** elapsed %e, max RSS %M' -- \
      $osh --ast-format __perf --tool syntax-tree $file | wc --bytes
  done
}

max-rss() {
  local osh=_bin/cxx-opt/osh
  ninja $osh

  for file in "${FILES[@]}"; do
    echo "___ parsing and pretty printing $file"
    echo

    /usr/bin/time --format '*** elapsed %e, max RSS %M' -- \
      $osh --ast-format text --tool syntax-tree $file | wc --bytes
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

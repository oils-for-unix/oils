#!/usr/bin/env bash
#
# Metrics for Oil bytecode produced by the OPy compiler.
#
# This is more like a metric than a benchmark.  In particular, we do NOT need
# to run it on multiple machines!  It doesn't need the provenance of binaries
# and so forth.
#
# But it IS like a benchmark in that we use R to analyze data and want HTML
# reports.
#
# NOTE: We will eventually have benchmarks for OPy compile time.
#
# Usage:
#   ./bytecode.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source test/common.sh

readonly BASE_DIR=_tmp/metrics/bytecode

write-opcodes() {
  # 119 ops?
  PYTHONPATH=. python2 > _tmp/opcodes-defined.txt -c '
from opy.lib import opcode
names = sorted(opcode.opmap)
for n in names:
  print(n)
'
  wc -l _tmp/opcodes-defined.txt  # 119 defined
}

# NOTE: We analyze ~76 bytecode files.  This outputs produces 5 TSV2 files that
# are ~131K rows in ~8.5 MB altogether.  The biggest table is the 'ops' table.

opy-dis-tables() {
  local out_dir=$BASE_DIR/opy-dis-tables
  mkdir -p $out_dir

  # Pass the .pyc files in the bytecode-opy.zip file to 'opyc dis'

  # The .pyc files look like _build/oil/bytecode-opy/os.pyc
  time cat _build/oil/opy-app-deps.txt \
    | awk ' $1 ~ /\.pyc$/ { print $1 }' \
    | xargs -- bin/opyc dis-tables $out_dir

  wc -l $out_dir/*.tsv2
}

# Hm it seems like build/prepare.sh build-python is necessary for this?
cpython-dis-tables() {
  local out_dir=$BASE_DIR/cpython-dis-tables
  mkdir -p $out_dir
  # The .py files look like /home/andy/git/oilshell/oil/Python-2.7.13/Lib/os.py
  time cat _build/oil/opy-app-deps.txt \
    | awk ' $1 ~ /\.py$/ { print $1 "c" }' \
    | xargs -- bin/opyc dis-tables $out_dir

  wc -l $out_dir/*.tsv2
}

# CPython:
#
#   9143 _tmp/metrics/bytecode/cpython/consts.tsv2
#   3956 _tmp/metrics/bytecode/cpython/flags.tsv2
#   1858 _tmp/metrics/bytecode/cpython/frames.tsv2
#  19808 _tmp/metrics/bytecode/cpython/names.tsv2
#  76504 _tmp/metrics/bytecode/cpython/ops.tsv2
# 111269 total
#
# OPy:
#   8338 _tmp/metrics/bytecode/consts.tsv2  # fewer docstrings?
#   3909 _tmp/metrics/bytecode/flags.tsv2
#   1857 _tmp/metrics/bytecode/frames.tsv2
#  35609 _tmp/metrics/bytecode/names.tsv2
#  80396 _tmp/metrics/bytecode/ops.tsv2
# 130109 total
#
# Yes I see there is bug in the names.
# Frames are almost exactly the same, which I expected.


report() {
  R_LIBS_USER=$R_PATH metrics/bytecode.R "$@"
}

# Reads the 5 tables and produces some metrics.
metrics-opy() {
  report metrics $BASE_DIR/opy-dis-tables
}

compare() {
  report compare $BASE_DIR/cpython-dis-tables $BASE_DIR/opy-dis-tables
}

# Reads a .py / .pyc manifest and calculates the ratio of input/output file
# sizes.
src-bin-ratio() {
  # Pass the manifest and the base directory of .pyc files.
  report src-bin-ratio _build/oil/all-deps-py.txt _build/oil/bytecode-opy
}

run-for-release() {
  write-opcodes  # _tmp/opcodes-defined.txt, for analysis

  opy-dis-tables
  cpython-dis-tables

  local out

  out=$BASE_DIR/oil-with-opy.txt
  report metrics $BASE_DIR/opy-dis-tables > $out
  log "Wrote $out"

  out=$BASE_DIR/oil-with-cpython.txt
  report metrics $BASE_DIR/cpython-dis-tables > $out
  log "Wrote $out"

  out=$BASE_DIR/src-bin-ratio-with-opy.txt
  src-bin-ratio > $out
  log "Wrote $out"

  out=$BASE_DIR/overview.txt
  compare > $out
  log "Wrote $out"
}

# TODO:
# - opy/callgraph.py should output a table too
#   - then take the difference to find which ones are unused
#   - problem: it doesn't have unique names?  Should we add (name, firstlineno)
#     to the key?  That is only stable for the exact same version.
# - compare bytecode vs CPython
#   - I think there is a bug with 'names' ?

# maybe:
# - analyze native code for OVM from GCC/Clang output?

"$@"

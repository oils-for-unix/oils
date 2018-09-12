#!/bin/bash
#
# Usage:
#   ./opy.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

# This is like the pydeps.  The Makefile duplicates this a bit.
lines() {
  cat _build/oil/all-deps-py.txt | awk '{print $1}' | xargs wc -l | sort -n
}

# NOTE: We analyze ~76 bytecode files.  This outputs produces 5 TSV2 files that
# are ~131K rows in ~8.5 MB altogether.  The biggest table is the 'ops' table.

dis-tables() {
  local out_dir=_tmp/metrics/bytecode
  mkdir -p $out_dir

  # Pass the .pyc files in the bytecode-opy.zip file to 'opyc dis'
  time cat _build/oil/opy-app-deps.txt \
    | awk ' $1 ~ /\.pyc$/ { print $1 }' \
    | xargs -- bin/opyc dis-tables $out_dir

  wc -l $out_dir/*.tsv2
}

# TODO:
# - opy/callgraph.py should output a table too
#   - then take the difference to find which ones are unused
#   - problem: it doesn't have unique names?  Should we add (name, firstlineno)
#     to the key?  That is only stable for the exact same version.
# - compare vs CPython

# maybe:
# - analyze native code for OVM from GCC/Clang output?

"$@"

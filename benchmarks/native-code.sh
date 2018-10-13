#!/bin/bash
#
# Usage:
#   ./native-code.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source test/common.sh  # for $R_PATH

readonly BASE_DIR=_tmp/metrics/native-code

# Size profiler for binaries.
bloaty() {
  ~/git/other/bloaty/bloaty "$@"
}

pylibc-symbols() {
  symbols _devbuild/py-ext/x86_64/libc.so
}

fastlex-symbols() {
  symbols _devbuild/py-ext/x86_64/fastlex.so
}

symbols() {
  local obj=$1
  nm $obj
  echo

  bloaty $obj
  echo

  # fastlex_MatchToken is 21.2 KiB.  That doesn't seem to large compared ot
  # the 14K line output?
  bloaty -d symbols $obj
  echo

  ls -l $obj
  echo
}

# Big functions:
# - PyEval_EvalFrameEx (38 KiB)
# - fastlex_MatchOSHToken (22.5 KiB)
# - convertitem() in args.py (9.04 KiB)
# - PyString_Format() in args.py (6.84 KiB)
#
# Easy removals:
# - marshal_dumps and marshal_dump!  We never use those.
# - Remove all docstrings!!!  Like sys_doc.

cpython-bloat() {
  # NOTE: This is different than the release binary!
  # ovm-opt.stripped doesn't show a report.
  local file=_build/oil/ovm-opt

  # Slightly different.
  #local file=_build/oil/ovm-dbg

  #bloaty -n 30 -d symbols $file

  # Full output
  # 3,588 lines!
  bloaty --tsv -n 0 -d symbols $file 
}

report() {
  R_LIBS_USER=$R_PATH benchmarks/native-code.R "$@"
}

run-for-release() {
  mkdir -p $BASE_DIR
  cpython-bloat | tee $BASE_DIR/symbols.tsv
  report metrics $BASE_DIR
}


"$@"

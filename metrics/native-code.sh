#!/bin/bash
#
# Usage:
#   ./native-code.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source test/common.sh  # for $R_PATH

readonly OVM_BASE_DIR=_tmp/metrics/ovm
readonly OIL_BASE_DIR=_tmp/metrics/oil-native

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

compileunits() {
  # Hm there doesn't seem to be a way to do this without
  local file=${1:-_build/oil/ovm-dbg}

  #local file=_build/oil/ovm-opt
  #local sym=_build/oil/ovm-opt.symbols

  bloaty --tsv -n 0 -d compileunits $file 
}

symbols() {
  # NOTE: This is different than the release binary!
  # ovm-opt.stripped doesn't show a report.
  local file=${1:-_build/oil/ovm-opt}

  # Slightly different.
  #local file=_build/oil/ovm-dbg

  #bloaty -n 30 -d symbols $file

  # Full output
  # 3,588 lines!
  bloaty --tsv -n 0 -d symbols $file 
}

report() {
  R_LIBS_USER=$R_PATH metrics/native-code.R "$@"
}

build-ovm() {
  make _build/oil/ovm-{dbg,opt}
}

collect-and-report() {
  local base_dir=$1
  local dbg=$2
  local opt=$3

  mkdir -p $base_dir
  symbols $opt > $base_dir/symbols.tsv

  # Really 'transation units', but bloaty gives it that name.
  compileunits $dbg > $base_dir/compileunits.tsv

  head $base_dir/symbols.tsv $base_dir/compileunits.tsv

  report metrics $base_dir $dbg $opt | tee $base_dir/overview.txt
}

readonly OIL_VERSION=$(head -n 1 oil-version.txt)

run-for-release() {
  build-ovm

  local dbg=_build/oil/ovm-dbg
  local opt=_build/oil/ovm-opt

  collect-and-report $OVM_BASE_DIR $dbg $opt

  local bin_dir="../benchmark-data/src/oil-native-$OIL_VERSION"
  collect-and-report $OIL_BASE_DIR $bin_dir/_bin/osh_parse.{dbg,opt}
}

"$@"

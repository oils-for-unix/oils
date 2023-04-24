#!/usr/bin/env bash
#
# Usage:
#   metrics/native-code.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source build/dev-shell.sh  # put bloaty in $PATH, R_LIBS_USER

readonly OVM_BASE_DIR=_tmp/metrics/ovm
readonly OIL_BASE_DIR=_tmp/metrics/oils-for-unix

pylibc-symbols() {
  symbols _devbuild/py-ext/x86_64/libc.so
}

fastlex-symbols() {
  symbols _devbuild/py-ext/x86_64/fastlex.so
}

print-symbols() {
  local obj=$1
  ls -l $obj
  echo

  # Summary
  bloaty $obj
  echo

  # Top symbols
  # fastlex_MatchToken is 21.2 KiB.  That doesn't seem to large compared ot
  # the 14K line output?
  bloaty -d symbols $obj
  echo

  nm $obj
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

  # Full output
  # 3,588 lines!
  bloaty --tsv -n 0 -d symbols $file 
}

R-report() {
  metrics/native-code.R "$@"
}

build-ovm() {
  # 2022-12: hack for ./configure, because line_input failed to compile without
  # HAVE_READLINE See _build/oil/module_init.c
  # TODO: This metric should either be DELETED, or automated in the CI, so it
  # doesn't break

  ./configure

  make _build/oil/ovm-{dbg,opt}
}

collect-and-report() {
  local base_dir=$1
  local dbg=$2
  local opt=$3

  mkdir -p $base_dir

  print-symbols $opt > $base_dir/symbols.txt

  symbols $opt > $base_dir/symbols.tsv

  # Really 'transation units', but bloaty gives it that name.
  compileunits $dbg > $base_dir/compileunits.tsv

  head $base_dir/symbols.tsv $base_dir/compileunits.tsv

  # Hack for now
  if Rscript -e 'print("hi from R")'; then
    R-report metrics $base_dir $dbg $opt | tee $base_dir/overview.txt
  else
    echo 'R not detected' | tee $base_dir/overview.txt
  fi

  # For CI
  cat >$base_dir/index.html <<'EOF'
<a href="overview.txt">overview.txt</a> <br/>
<a href="compileunits.tsv">compileunits.tsv</a> <br/>
<a href="symbols.tsv">symbols.tsv</a> <br/>
<a href="symbols.txt">symbols.txt</a> <br/>
EOF
}

oils-for-unix() {
  ### Report on the ones we just built

  # TODO: could compare GCC and Clang once we have R on the CI images
  local -a targets=(_bin/cxx-{dbg,opt}/oils-for-unix)
  ninja "${targets[@]}"

  collect-and-report $OIL_BASE_DIR "${targets[@]}"

  ls -l $OIL_BASE_DIR
}

compare-gcc-clang() {
  ### Run by Soil 'cpp-coverage' task, because it has clang

  local -a targets=(
    _bin/{clang,cxx}-dbg/oils-for-unix
    _bin/{clang,cxx}-opt/oils-for-unix.stripped
    _bin/cxx-{opt+bumpleak,opt+bumproot}/oils-for-unix.stripped
    )
  ninja "${targets[@]}"

  mkdir -p _tmp/metrics
  ls -l "${targets[@]}" | tee _tmp/metrics/compare-gcc-clang.txt
}

readonly OIL_VERSION=$(head -n 1 oil-version.txt)

run-for-release() {
  build-ovm

  local dbg=_build/oil/ovm-dbg
  local opt=_build/oil/ovm-opt

  collect-and-report $OVM_BASE_DIR $dbg $opt

  # TODO: consolidate with benchmarks/common.sh, OSH_CPP_BENCHMARK_DATA
  # For some reason _bin/cxx-opt/ and _bin/cxx-opt-sh can differ by a few bytes
  local bin_dir="../benchmark-data/src/oils-for-unix-$OIL_VERSION"
  collect-and-report $OIL_BASE_DIR $bin_dir/_bin/cxx-{dbg,opt}-sh/oils-for-unix
}

dupe-strings() {
  ### Check for NUL-terminated strings

  python2 -c '
import collections
import re
import sys

with open(sys.argv[1]) as f:
  contents = f.read()
strs = re.split("\\0", contents)

printable = re.compile("[ -~]+$")

d = collections.Counter()
for s in strs:
  if len(s) > 1 and printable.match(s):
    d[s] += 1

for s, count in d.most_common()[:50]:
  if count == 1:
    break
  print("%5d %r" % (count, s))

' "$@"
}

# Results: 
# Found StrFromC() and len() duplication

oil-dupe-strings() {
  local bin=_bin/cxx-opt/oils-for-unix.stripped
  #local bin=_bin/clang-opt/oils-for-unix.stripped
  ninja $bin

  dupe-strings $bin
}

"$@"

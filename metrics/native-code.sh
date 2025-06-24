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
  # fastlex_MatchToken is 21.2 KiB.  That doesn't seem to large compared to
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
  local file=${1:-_build/oils-ref/ovm-dbg}

  #local file=_build/oils-ref/ovm-opt
  #local sym=_build/oils-ref/ovm-opt.symbols

  bloaty --tsv -n 0 -d compileunits $file 
}

symbols() {
  # NOTE: This is different than the release binary!
  # ovm-opt.stripped doesn't show a report.
  local file=${1:-_build/oils-ref/ovm-opt}

  # Full output
  # 3,588 lines!
  bloaty --tsv -n 0 -d symbols $file 
}

R-report() {
  metrics/native-code.R "$@"
}

build-ovm() {
  # 2022-12: hack for ./configure, because line_input failed to compile without
  # HAVE_READLINE See _build/oils-ref/module_init.c
  # TODO: This metric should either be DELETED, or automated in the CI, so it
  # doesn't break

  ./configure

  make _build/oils-ref/ovm-{dbg,opt}
}

collect-and-report() {
  local base_dir=$1
  local dbg=$2
  local opt=$3

  mkdir -p $base_dir

  print-symbols $opt > $base_dir/symbols.txt

  symbols $opt > $base_dir/symbols.tsv

  # Really 'translation units', but bloaty gives it that name.
  compileunits $dbg > $base_dir/compileunits.tsv

  head $base_dir/symbols.tsv $base_dir/compileunits.tsv

  # Hack for now
  if Rscript -e 'print("hi from R")'; then
    R-report metrics $base_dir $dbg $opt | tee $base_dir/overview.txt
  else
    echo 'R not detected' | tee $base_dir/overview.txt
  fi
}

oils-for-unix() {
  ### Report on the ones we just built

  # Use DWARF 4 for bloaty, as we do in
  #   devtools/release.sh _build-oils-benchmark-data
  CXXFLAGS=-gdwarf-4 soil/cpp-tarball.sh build-like-ninja dbg opt
  #soil/cpp-tarball.sh build-like-ninja dbg opt

  collect-and-report $OIL_BASE_DIR _bin/cxx-{dbg,opt}/oils-for-unix

  ls -l $OIL_BASE_DIR
}

compare-gcc-clang() {
  ### Run by Soil 'cpp-coverage' task, because it has clang

  local -a targets=(
    _bin/{clang,cxx}-opt/bin/oils_for_unix.mycpp.stripped
    _bin/{clang,cxx}-opt/bin/oils_for_unix.mycpp-souffle.stripped
    _bin/cxx-{opt+bumpleak,opt+bumproot,opt+bigint}/bin/oils_for_unix.mycpp.stripped
    _bin/{clang,cxx}-opt/yaks/yaks_main.mycpp.stripped
    #_bin/cxx-{opt+bumpleak,opt+bumproot}/yaks/yaks_main.mycpp.stripped
    )
  ninja "${targets[@]}"

  mkdir -p _tmp/metrics
  ls -l --sort=none "${targets[@]}" | tee _tmp/metrics/compare-gcc-clang.txt
}

readonly OILS_VERSION=$(head -n 1 oils-version.txt)

run-for-release() {
  # 2024-08: Not building with DWARF 4
  if false; then
    build-ovm

    local dbg=_build/oils-ref/ovm-dbg
    local opt=_build/oils-ref/ovm-opt

    collect-and-report $OVM_BASE_DIR $dbg $opt
  fi

  # TODO: consolidate with benchmarks/common.sh, OSH_CPP_TWO
  # For some reason _bin/cxx-opt/ and _bin/cxx-opt-sh can differ by a few bytes
  local bin_dir="../benchmark-data/src/oils-for-unix-$OILS_VERSION"
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
  local bin=_bin/cxx-opt/bin/oils_for_unix.mycpp.stripped
  #local bin=_bin/clang-opt/oils-for-unix.stripped
  ninja $bin

  dupe-strings $bin
}

"$@"

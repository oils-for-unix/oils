#!/bin/bash
#
# Usage:
#   ./mycpp.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source build/common.sh  # for $CLANG_DIR_RELATIVE, $PREPARE_DIR

readonly THIS_DIR=$(dirname $(readlink -f $0))
readonly REPO_ROOT=$THIS_DIR/..

# set by mycpp/setup.sh
readonly MYPY_REPO=${MYPY_REPO:-~/git/languages/mypy}

# for 'perf'.  Technically this may slow things down, but it was in the noise
# on parsing configure-coreutils.
CPPFLAGS="$CXXFLAGS -fno-omit-frame-pointer"

# this flag is only valid in Clang
#CPPFLAGS="$CPPFLAGS -ferror-limit=1000"

# Always build with Address Sanitizer
readonly DBG_FLAGS="$CPPFLAGS -O0 -g"

export ASAN_SYMBOLIZER_PATH=$CLANG_DIR_RELATIVE/bin/llvm-symbolizer
# https://github.com/google/sanitizers/wiki/AddressSanitizerLeakSanitizer
export ASAN_OPTIONS='detect_leaks=0'

asdl-demo() {
  build/dev.sh oil-asdl-to-cpp
  $CXX -o _bin/oil_mycpp $DBG_FLAGS \
    -I _build/cpp \
    -I _devbuild/gen \
    -I mycpp \
    bin/oil.cc mycpp/mylib.cc -lstdc++

  echo '___'

  _bin/oil_mycpp
}

mycpp() {
  ### Run mycpp (in a virtualenv because it depends on Python 3 / MyPy)

  # created by mycpp/run.sh

  ( 
    # for _OLD_VIRTUAL_PATH error on Travis?
    set +o nounset
    set +o pipefail
    set +o errexit

    source mycpp/_tmp/mycpp-venv/bin/activate
    time PYTHONPATH=$MYPY_REPO MYPYPATH=$REPO_ROOT:$REPO_ROOT/native \
      mycpp/mycpp_main.py "$@"
  )
}

example-skeleton() {
  local namespace=$1
  shift

  cat <<EOF
#include "mylib.h"

EOF

  cat "$@"

  # TODO: This should find main(List<str>* argv) in the namespace
  cat <<EOF

int main(int argc, char **argv) {
  $namespace::run_tests();
}
EOF

}

cpp-skeleton() {
  local name=$1
  shift

  cat <<EOF
// $name.cc: translated from Python by mycpp

#include "preamble.h"  // hard-coded stuff

EOF

  cat "$@"

  cat <<EOF
int main(int argc, char **argv) {
  gc_heap::gHeap.Init(400 << 20);  // 400 MiB matches dumb_alloc.cc
  auto* args = Alloc<List<Str*>>();
  for (int i = 0; i < argc; ++i) {
    args->append(Alloc<Str>(argv[i]));
  }
  int status;

  // For benchmarking
  char* repeat = getenv("REPEAT");
  if (repeat) {
    Str* r = Alloc<Str>(repeat);
    int n = to_int(r);
    log("Running %d times", n);
    for (int i = 0; i < n; ++i) { 
      status = $name::main(args);
    }
    // TODO: clear memory?
  } else {
    status = $name::main(args);
  }

  dumb_alloc::Summarize();
  return status;
}

// hard-coded definitions!
#include "postamble.cc"
EOF

}

compile() {
  local out=$1
  shift

  local flags="$CPPFLAGS"
  local link_flags=''
  case $out in
    *.opt)
      flags="$CPPFLAGS -O2 -g -D DUMB_ALLOC"
      # To debug crash with 8 byte alignment
      #flags="$CPPFLAGS -O0 -g -D DUMB_ALLOC -D ALLOC_LOG"
      ;;
    *.uftrace)
      # -O0 creates a A LOT more data.  But sometimes we want to see the
      # structure of the code.
      # vector::size(), std::forward, len(), etc. are not inlined.
      # Also List::List, Tuple2::at0, etc.
      #local opt='-O2'
      local opt='-O0'

      # Do we want DUMB_ALLOC here?
      flags="$CPPFLAGS $opt -g -pg"
      ;;
    *.malloc)
      flags="$CPPFLAGS -O2 -g"
      ;;
    *.tcmalloc)
      flags="$CPPFLAGS -O2 -g -D TCMALLOC"
      link_flags='-ltcmalloc'
      ;;
    *.asan)
      # Note: Clang's ASAN doesn't like DUMB_ALLOC, but GCC is fine with it
      flags="$CPPFLAGS -O0 -g -fsanitize=address"
      ;;
    *.alloclog)
      # debug flags
      flags="$CPPFLAGS -O0 -g -D DUMB_ALLOC -D ALLOC_LOG"
      ;;
    *.dbg)
      # debug flags
      flags="$CPPFLAGS -O0 -g"
      ;;
  esac

  # Hack to remove optview::Exec
  case $out in
    *osh_parse*)
      flags="$flags -D OSH_PARSE"
      ;;
    *osh_eval*)
      flags="$flags -D OSH_EVAL"
      ;;
  esac

  # flags are split
  $CXX $flags \
    -I . \
    -I mycpp \
    -I cpp \
    -I _build/cpp \
    -I _devbuild/gen \
    -o $out \
    "$@" \
    $link_flags \
    -lstdc++
}

mycpp-demo() {
  ### Translate, compile, and run a program

  local name=${1:-conditional}

  local raw=_tmp/${name}_raw.cc 
  mycpp mycpp/examples/$name.py > $raw

  local cc=_tmp/$name.cc
  example-skeleton $name $raw > $cc

  compile _tmp/$name $cc mycpp/mylib.cc

  # Run it
  _tmp/$name
}

compile-slice() {
  local name=${1:-osh_eval}
  # Add -opt to make it opt
  local suffix=${2:-.dbg}

  shift 2

  mkdir -p _bin

  # Note: can't use globs here because we have _test.cc
  time compile _bin/$name$suffix _build/cpp/${name}.cc \
    mycpp/gc_heap.cc \
    mycpp/mylib.cc \
    cpp/core_pyos.cc \
    cpp/core_pyutil.cc \
    cpp/frontend_flag_spec.cc \
    cpp/frontend_match.cc \
    cpp/frontend_tdop.cc \
    cpp/osh_arith_parse.cc \
    cpp/osh_bool_stat.cc \
    cpp/pgen2_parse.cc \
    _build/cpp/runtime_asdl.cc \
    _build/cpp/syntax_asdl.cc \
    _build/cpp/hnode_asdl.cc \
    _build/cpp/id_kind_asdl.cc \
    _build/cpp/consts.cc \
    _build/cpp/arith_parse.cc \
    _build/cpp/arg_types.cc \
    cpp/dumb_alloc.cc \
    cpp/errno_.cc \
    cpp/fcntl_.cc \
    cpp/posix.cc \
    cpp/signal_.cc \
    cpp/libc.cc \
    "$@"

  #2>&1 | tee _tmp/compile.log
}

compile-slice-opt() {
  local name=${1:-osh_eval}
  compile-slice $name '.opt'

  local opt=_bin/$name.opt
  local stripped=_bin/$name.opt.stripped 
  local symbols=_bin/$name.opt.symbols 

  # As done in the Makefile for Python app bundle
  strip -o $stripped $opt

  # Move the symbols elsewhere and add a link to them.
  if command -v objcopy > /dev/null; then
    objcopy --only-keep-debug $opt $symbols
    objcopy --add-gnu-debuglink=$symbols $stripped
  fi
}

compile-slice-alloclog() { compile-slice "${1:-}" '.alloclog'; }
compile-slice-asan() { compile-slice "${1:-}" '.asan'; }
compile-slice-uftrace() { compile-slice "${1:-}" '.uftrace'; }
compile-slice-tcmalloc() { compile-slice "${1:-}" '.tcmalloc'; }
compile-slice-malloc() { compile-slice "${1:-}" '.malloc'; }

all-variants() {
  local name=${1:-osh_eval}

  compile-slice $name ''  # .dbg version is default
  compile-slice-opt $name

  compile-slice-alloclog $name
  compile-slice-asan $name
  compile-slice-uftrace $name
  compile-slice-tcmalloc $name

  # show show linking against libasan, libtcmalloc, etc
  ldd _bin/$name*
  echo
  ls -l _bin/$name*
}

readonly TMP=_devbuild/tmp

osh-eval-manifest() {
  # _devbuild is ASDL stuff
  # frontend metaprogramming: */*_def.py
  # core/process.py - not ready
  # pyutil.py -- Python only (Resource Loader, etc.)
  # pgen2/parse.py: prefer hand-written C

  # TODO: could be pyoptview,pyconsts,pymatch,pyflag

  local exclude='_devbuild/|.*_def\.py|core/py.*\.py|pybase.py|optview.py|match.py|path_stat.py|bool_stat.py|consts.py|pgen2/parse.py|oil_lang/objects.py|flag_spec.py|builtin_process.py'

  egrep -v "$exclude" types/osh-eval-manifest.txt
}

osh-eval() {
  ### Translate bin/osh_eval.py

  local name=${1:-osh_eval}

  local tmp=$TMP
  mkdir -p $tmp

  local raw=$tmp/${name}_raw.cc 

  local cc=_build/cpp/$name.cc
  local h=_build/cpp/$name.h

  #if false; then
  if true; then
    # relies on splitting
    mycpp \
      --header-out $h \
      --to-header frontend.args \
      --to-header asdl.runtime \
      --to-header asdl.format \
      $(osh-eval-manifest) > $raw 
  fi

  cpp-skeleton $name $raw > $cc

  compile-slice 'osh_eval' '.dbg'
}

asdl-runtime() {
  ### Translate ASDL deps for unit tests

  # - MESSY: asdl/runtime.h contains the SAME DEFINITIONS as
  #   _build/cpp/osh_eval.h.  But we use it to run ASDL unit tests without
  #   depending on Oil.

  local name=asdl_runtime
  local raw=$TMP/${name}_raw.cc 

  mycpp \
    --header-out $TMP/runtime.h \
    --to-header asdl.runtime \
    --to-header asdl.format \
    $REPO_ROOT/{asdl/runtime,asdl/format,core/ansi,pylib/cgi,qsn_/qsn}.py \
    > $raw 

  local cc=asdl/runtime.cc

  { cat <<EOF
// asdl/runtime.h: This file generated by mycpp from asdl/{runtime,format}.py

#include "mylib.h"
#include "hnode_asdl.h"
#include "qsn_qsn.h"

// For hnode::External in asdl/format.py.  TODO: Remove this when that is removed.
inline Str* repr(void* obj) {
  assert(0);
}

EOF
    cat $TMP/runtime.h
  } > asdl/runtime.h

  cat $raw > $cc

  #compile-slice $name '.dbg'
}

port-os-path() {

  local name=os_path
  local raw=$TMP/${name}_raw.cc 

  mycpp \
    $REPO_ROOT/pylib/os_path.py \
    > $raw 
}

osh-parse-asan() {
  ### Wrapper for ASAN env vars, to show stack strace

  _bin/osh_parse.asan "$@"
}

osh-eval-asan() {
  ### Wrapper for ASAN env vars, to show stack strace

  _bin/osh_eval.asan "$@"
}

size-profile() {
  wc -l _build/cpp/osh_parse.cc

  local bin=_bin/osh_parse.opt

  ls -l _bin/osh_parse*

  bloaty -d compileunits $bin
  echo
  bloaty -d symbols $bin
}

smoke-manifest() {
  for file in */*.sh; do
  #for file in spec/*.sh; do
    case $file in
      # Exclude _tmp/ etc.
      _*) continue ;;

      # the STDOUT blocks have invalid syntax
      # TODO: Enable this as a separate test of syntax errors
      #spec/*) continue ;;

      # pgen2 not done
      spec/oil-*) continue ;;
      spec/arith-context.test.sh) continue ;;
      spec/builtin-eval-source.test.sh) continue ;;

      # This has Oil syntax
      test/oil-runtime-errors.sh) continue ;;
    esac

    echo $file
  done
}

py-parse() {
  local id=$1
  local file=$2

  local out=_tmp/osh-parse-smoke/py/$id
  bin/osh --ast-format text -n $file > $out
}

cpp-parse() {
  local id=$1
  local file=$2

  local out=_tmp/osh-parse-smoke/cpp/$id
  _bin/osh_parse.asan $file > $out
}

dump-asts() {
  ### Dump ASTs produced by Python and C++ 

  local manifest='_tmp/smoke-manifest.txt'

  # TODO: make the first 10 match

  # nl gives the ID
  smoke-manifest | nl > $manifest

  rm -f _tmp/osh-parse-smoke/{py,cpp}/*
  mkdir -p _tmp/osh-parse-smoke/{py,cpp}

  set +o errexit
  time cat $manifest | xargs --verbose -n 2 -- $0 py-parse
  time cat $manifest | xargs --verbose -n 2 -- $0 cpp-parse
  set -o errexit
}

compare-asts() {
  mkdir -p _tmp/osh-parse-smoke/{py,cpp,diff}

  local num_failed=0
  for path in _tmp/osh-parse-smoke/py/*; do
    echo $path
    local diff_path=${path//py/diff}
    set +o errexit
    diff -u $path ${path//py/cpp} > $diff_path
    local status=$?
    set -o errexit
    if test $status -ne 0; then
      num_failed=$((num_failed + 1))
    fi

  done

  echo "$num_failed differences"
}

osh-parse-smoke() {
  ### Run C++ version bin/osh_parse on our shell scripts (with ASAN on)

  local python=${1:-}

  local parse_errors=''
  local crashed=''

  while read file; do
    set +o errexit

    echo "_____ $file"

    if test -n "$python"; then
      bin/osh -n $file | wc -l
    else
      local osh_parse=_bin/osh_eval.asan 
      $osh_parse -n $file | wc -l

      # This also works
      #local osh_eval=_bin/osh_eval.asan 
      #$osh_eval -n $file | wc -l
    fi

    case $? in
      0)
        ;;
      2)
        parse_errors+=" $file"
        ;;
      *)
        crashed+=" $file"
        ;;
    esac

    set -o errexit
  done < <(smoke-manifest)

  echo
  echo "Can't parse:"
  echo
  for file in $parse_errors; do  # split words
    echo $file
  done

  # A couple spec tests fail because they have what looks like Oil expressions
  echo
  echo 'CRASHED:'
  echo
  for file in $crashed; do  # split words
    echo $file
  done
}

osh-eval-smoke() {
  ### Run osh_eval.dbg over a bunch of shell scripts
  local osh_eval=${1:-_bin/osh_eval.dbg}

  # Problem: all while loops go infinitely now...

  local parse_errors=''
  local fail=''

  for file in spec/[01a]*.sh; do
    set +o errexit

    echo "_____ $file"

    $osh_eval $file

    case $? in
      0)
        ;;
      2)
        parse_errors+=" $file"
        ;;
      *)
        fail+=" $file"
        ;;
    esac

    set -o errexit
  done

  echo
  echo "Can't parse:"
  echo
  for file in $parse_errors; do  # split words
    echo $file
  done

  # A couple spec tests fail because they have what looks like Oil expressions
  echo
  echo 'FAILED:'
  echo
  for file in $fail; do  # split words
    echo $file
  done
}

osh-eval-demo() {
  local osh_eval=${1:-_bin/osh_eval.dbg}
  types/oil-slice.sh demo "$osh_eval"
}

#
# Public
#

# Used by devtools/release.sh and devtools/release-native.sh
# This is the demo we're releasing to users!
compile-oil-native() {
  compile-slice osh_eval ''
}

compile-oil-native-opt() {
  compile-slice-opt osh_eval ''
}

compile-oil-native-asan() {
  compile-slice-asan osh_eval ''
}

# Demo for the oil-native tarball.
tarball-demo() {
  mkdir -p _bin

  time compile-oil-native-opt

  local bin=_bin/osh_eval.opt.stripped
  ls -l $bin

  echo
  echo "You can now run $bin.  Example:"
  echo

  set -o xtrace
  $bin -n -c 'echo "hello $name"'
}

if test $(basename $0) = 'mycpp.sh'; then
  "$@"
fi

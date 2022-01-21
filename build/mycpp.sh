#!/usr/bin/env bash
#
# Usage:
#   build/mycpp.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source build/common.sh  # for $CLANG_DIR_RELATIVE

REPO_ROOT=$(cd $(dirname $0)/.. && pwd)
readonly REPO_ROOT

source mycpp/common.sh  # MYPY_REPO

# for 'perf'.  Technically this may slow things down, but it was in the noise
# on parsing configure-coreutils.
CPPFLAGS="$CXXFLAGS -fno-omit-frame-pointer"

# this flag is only valid in Clang, doesn't work in continuous build
if test "$CXX" = "$CLANGXX"; then
  CPPFLAGS="$CPPFLAGS -ferror-limit=1000"
fi

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

  # Avoid memset().  TODO: remove this hack!
  flags="$flags -D NO_GC_HACK"

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

# what osh_eval.cc needs to compile
readonly -a DEPS_CC=(
    cpp/core_pyos.cc \
    cpp/core_pyutil.cc \
    cpp/frontend_flag_spec.cc \
    cpp/frontend_match.cc \
    cpp/frontend_tdop.cc \
    cpp/osh_arith_parse.cc \
    cpp/osh_bool_stat.cc \
    cpp/pgen2_parse.cc \
    cpp/pylib_os_path.cc \
    _build/cpp/runtime_asdl.cc \
    _build/cpp/syntax_asdl.cc \
    _build/cpp/hnode_asdl.cc \
    _build/cpp/id_kind_asdl.cc \
    _build/cpp/consts.cc \
    _build/cpp/arith_parse.cc \
    _build/cpp/arg_types.cc \
    cpp/dumb_alloc.cc \
    cpp/fcntl_.cc \
    cpp/posix.cc \
    cpp/signal_.cc \
    cpp/libc.cc \
)

readonly -a GC_RUNTIME=( mycpp/{gc_heap,mylib2,my_runtime}.cc )

readonly -a OLD_RUNTIME=( mycpp/{gc_heap,mylib}.cc )

compile-slice() {
  ### Build done outside ninja in _bin/

  local name=${1:-osh_eval}
  # Add -opt to make it opt
  local suffix=${2:-.dbg}

  shift 2

  mkdir -p _bin

  local -a runtime
  if test -n "${GC:-}"; then
    # Not ready for this yet.  Need list_contains() etc.
    runtime=( "${GC_RUNTIME[@]}" )
  else
    runtime=( "${OLD_RUNTIME[@]}" )
  fi

  # Note: can't use globs here because we have _test.cc
  time compile _bin/$name$suffix _build/cpp/${name}.cc \
    "${runtime[@]}" "${DEPS_CC[@]}" \
    "$@"
}

ninja-compile() {
  # Invoked by ninja (also in _bin/)

  local in=$1
  local out=$2

  local -a runtime
  if test -n "${GC:-}"; then
    # Not ready for this yet.  Need list_contains() etc.
    runtime=( "${GC_RUNTIME[@]}" )
  else
    runtime=( "${OLD_RUNTIME[@]}" )
  fi

  # Note: can't use globs here because we have _test.cc
  time compile $out $in \
    "${runtime[@]}" "${DEPS_CC[@]}"
}

strip_() {
  ### Invoked by ninja

  local in=$1
  local stripped=$2
  local symbols=$3

  strip -o $stripped $in

  objcopy --only-keep-debug $in $symbols
  objcopy --add-gnu-debuglink=$symbols $stripped
}

readonly TMP=_devbuild/tmp

# TODO: Fix all this code to use mylib2/my_runtime
mylib-audit() { 
  grep --color mylib.h cpp/*
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
  compile-slice osh_eval '.opt'

  local in=_bin/osh_eval.opt
  local out=$in.stripped
  strip -o $out $in
}

# Demo for the oil-native tarball.
# Notes:
# - This should not rely on Ninja!  Ninja is for the dev build.
# - It should also not require 'objcopy'

tarball-demo() {
  mkdir -p _bin

  time compile-slice osh_eval '.opt'

  local bin=_bin/osh_eval.opt.stripped

  ls -l $bin

  echo
  echo "You can now run $bin.  Example:"
  echo

  set -o xtrace
  $bin -n -c 'echo "hello $name"'
}

audit-tuple() {
  fgrep -n --color 'Alloc<Tuple' _build/cpp/osh_eval.cc
}

if test $(basename $0) = 'mycpp.sh'; then
  "$@"
fi

#!/usr/bin/env bash
#
# OLD FILE: Moved to build/{translate,native,native-steps}.sh
# May delete this.
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

#
# Public
#

audit-tuple() {
  fgrep -n --color 'Alloc<Tuple' _build/cpp/osh_eval.cc
}

if test $(basename $0) = 'mycpp.sh'; then
  "$@"
fi

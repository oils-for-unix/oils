#!/bin/bash
#
# Usage:
#   ./mycpp.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source build/common.sh  # for $CLANG_DIR_RELATIVE, $PREPARE_DIR

readonly REPO_ROOT=~/git/oilshell/oil

readonly MYPY_REPO=~/git/languages/mypy

# note: -Weverything is more than -Wall, but too many errors now.
CPPFLAGS='-std=c++11 -Wall'

# sign-compare disabled because of int i < v_.size()?  Should I use size_t?
GCC_FLAGS='-fpermissive -Wno-sign-compare'

# Temporary hack for 'token* token' in GCC
# https://stackoverflow.com/questions/8843818/what-does-the-fpermissive-flag-do
CPPFLAGS="$CPPFLAGS $GCC_FLAGS"

# This flag is Clang-only
#-ferror-limit=1000'

# Always build with Address Sanitizer
readonly DBG_FLAGS="$CPPFLAGS -O0 -g -fsanitize=address"

readonly OPT_FLAGS="$CPPFLAGS -O2 -g"

#readonly CXX=$CLANG_DIR_RELATIVE/bin/clang++
readonly CXX=c++

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

  local out=$1
  shift

  # created by mycpp/run.sh
  ( source mycpp/_tmp/mycpp-venv/bin/activate
    time PYTHONPATH=$MYPY_REPO MYPYPATH=$REPO_ROOT:$REPO_ROOT/native \
      mycpp/mycpp_main.py "$@" > $out
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
  local namespace=$1
  shift

  cat <<EOF
#include "mylib.h"
#include "preamble.h"  // hard-coded stuff

EOF

  cat "$@"

  cat <<EOF
int main(int argc, char **argv) {
  //log("%p", arith_parse::kNullLookup[1].nud);
  auto* args = new List<Str*>();
  for (int i = 0; i < argc; ++i) {
    args->append(new Str(argv[i]));
  }
  return $namespace::main(args);
}
EOF

}

compile() {
  local out=$1
  shift

  local flags
  case $out in
    *.opt)
      flags=$OPT_FLAGS
      ;;
    *)
      flags=$DBG_FLAGS
      ;;
  esac

  # flags are split
  $CXX $flags \
    -I mycpp \
    -I cpp \
    -I _build/cpp \
    -I _devbuild/gen \
    -o $out \
    "$@" \
    -lstdc++
}

mycpp-demo() {
  ### Translate, compile, and run a program

  local name=${1:-conditional}

  local raw=_tmp/${name}_raw.cc 
  mycpp $raw mycpp/examples/$name.py

  local cc=_tmp/$name.cc
  example-skeleton $name $raw > $cc

  compile _tmp/$name $cc mycpp/mylib.cc

  # Run it
  _tmp/$name
}

osh-parse-preamble() {
  cat <<EOF
// osh_parse.cc: translated from Python by mycpp

EOF
}

compile-osh-parse() {
  local name=${1:-osh_parse}
  # Add -opt to make it opt
  local suffix=${2:-.asan}  # opt or dbg

  mkdir -p _bin

  # Note: can't use globs here because we have _test.cc
  compile _bin/$name$suffix _build/cpp/${name}.cc \
    mycpp/mylib.cc \
    cpp/frontend_match.cc \
    cpp/asdl_pretty.cc \
    cpp/frontend_tdop.cc \
    cpp/osh_arith_parse.cc \
    _build/cpp/syntax_asdl.cc \
    _build/cpp/hnode_asdl.cc \
    _build/cpp/id_kind_asdl.cc \
    _build/cpp/lookup.cc \
    _build/cpp/arith_parse.cc 
  #2>&1 | tee _tmp/compile.log
}

compile-osh-parse-opt() {
  compile-osh-parse '' '.opt'

  local opt=_bin/osh_parse.opt
  local stripped=_bin/osh_parse.opt.stripped 
  local symbols=_bin/osh_parse.opt.symbols 

  # As done in the Makefile for Python app bundle
  strip -o $stripped $opt

  # Move the symbols elsewhere and add a link to them.
  if command -v objcopy > /dev/null; then
    objcopy --only-keep-debug $opt $symbols
    objcopy --add-gnu-debuglink=$symbols $stripped
  fi
}

readonly TMP=_tmp/mycpp

# TODO: Conslidate this with types/osh-parse-manifest.txt?
readonly OSH_PARSE_FILES=(
  $REPO_ROOT/asdl/format.py 
  $REPO_ROOT/asdl/runtime.py 

  $REPO_ROOT/core/alloc.py 
  $REPO_ROOT/frontend/reader.py 
  $REPO_ROOT/frontend/lexer.py 
  $REPO_ROOT/pgen2/grammar.py 
  $REPO_ROOT/pgen2/parse.py 
  $REPO_ROOT/oil_lang/expr_parse.py 
  $REPO_ROOT/oil_lang/expr_to_ast.py 

  $REPO_ROOT/pylib/cgi.py
  # join(*p) is a problem
  #$REPO_ROOT/pylib/os_path.py

  $REPO_ROOT/osh/braces.py

  # This has errfmt.Print() which uses *args and **kwargs
  $REPO_ROOT/core/ui.py

  $REPO_ROOT/core/error.py
  $REPO_ROOT/core/main_loop.py

  $REPO_ROOT/osh/word_.py 
  $REPO_ROOT/osh/bool_parse.py 
  $REPO_ROOT/osh/word_parse.py
  $REPO_ROOT/osh/cmd_parse.py 
  $REPO_ROOT/osh/arith_parse.py 
  $REPO_ROOT/osh/tdop.py
  $REPO_ROOT/frontend/parse_lib.py
)

osh-parse() {
  local name=${1:-osh_parse}

  local tmp=$TMP
  mkdir -p $tmp

  local raw=$tmp/${name}_raw.cc 

  #if false; then
  if true; then
    mycpp $raw bin/$name.py "${OSH_PARSE_FILES[@]}"
  fi

  local cc=_build/cpp/$name.cc

  { osh-parse-preamble 
    cpp-skeleton $name $raw 
  } > $cc

  compile-osh-parse $name
}

run-osh-parse() {
  local code_str=${1:-'echo hi'}

  local name='osh_parse'
  local tmp=$TMP

  strip -o $tmp/${name}.stripped $tmp/$name
  ls -l $tmp

  # Run it
  $tmp/$name "$@"
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
      _bin/osh_parse.asan $file | wc -l
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

# TODO: We need a proper unit test framework
frontend-match-test() {
  local name='frontend_match_test'
  compile _bin/$name cpp/frontend_match_test.cc cpp/frontend_match.cc mycpp/mylib.cc

  _bin/$name
}

# Demo for the oil-native tarball.
tarball-demo() {
  mkdir -p _bin

  time compile-osh-parse-opt

  local bin=_bin/osh_parse.opt.stripped
  ls -l $bin

  echo
  echo "You can now run $bin.  Example:"
  echo

  set -o xtrace
  $bin -c 'echo "hello $name"'

}

"$@"

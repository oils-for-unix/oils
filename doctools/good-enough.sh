#!/usr/bin/env bash
#
# Lexing / Parsing experiment
#
# Usage:
#   doctools/good-enough.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)  # tsv-lib.sh uses this

#source build/dev-shell.sh  # 're2c' in path
source build/ninja-rules-cpp.sh

#source test/common.sh
#source test/tsv-lib.sh

#export PYTHONPATH=.

my-re2c() {
  local in=$1
  local out=$2

  # Copied from build/py.sh
  re2c -W -Wno-match-empty-string -Werror -o $out $in
}

readonly BASE_DIR=_tmp/good-enough

build() {
  local variant=${1:-asan}

  case $variant in
    asan)
      cxxflags='-O0 -fsanitize=address'
      ;;
    opt)
      cxxflags='-O2'
      ;;
    *)
      die "Invalid variant $variant"
      ;;
  esac

  mkdir -p $BASE_DIR

  local cc=doctools/good-enough.cc
  local h=$BASE_DIR/good-enough.h
  local bin=$BASE_DIR/good-enough

  my-re2c doctools/good-enough.re2c.h $h

  # Note: with cc, you need gnu99 instead of c99 for fdopen() and getline()

  # g++ - otherwise virtual functions don't work!

  g++ -std=c++11 -Wall -I $BASE_DIR $cxxflags \
    -o $bin $cc

  strip -o $bin.stripped $bin

  log "  CXX $cc"

}

readonly -a PY_TESTS=(
    'abc' '""'
    '"dq \" backslash \\"' '"missing ' 
    "'sq \\' backslash \\\\'" 
    '"line\n"' '"quote \" backslash \\ "' 
    '"\n"' 
    'hi # comment' 
    '"hi"  # comment'
    '(r"raw dq")'
    "(r'raw \\' sq')"

' "L1"  # first
  L2 # second' 

' def f():
    """docstring
    with "quote"
    """
    pass'

" def f():
    '''docstring
    with 'quote'
    '''
    pass"

    " print(r'''hello''')"
    ' print(r"""hi there""")'
)

readonly -a CPP_TESTS=(
  '#if 0'
  'not prepreproc #ifdef 0'
  "// comment can't "
  "f(); // comment isn't "

  # Char literal in C
  "'\\''"

  'void f(); /* multi-line
                comment
             */
  void g(int x);'

  'char* s = f(R"(one
  two
  three)");
  '
)

run-tests() {
  local bin=$BASE_DIR/good-enough

  build

  #$bin 12 '' abc

  #echo
  #$bin "${STRS[@]}"

  echo
  for s in "${PY_TESTS[@]}"; do
    echo "==== $s"
    echo "$s" | $bin # -l py
    echo
  done

  echo
  for s in "${CPP_TESTS[@]}"; do
    echo "==== $s"
    echo "$s" | $bin -l cpp
    echo
  done

  echo '/dev/null'
  $bin < /dev/null
}

myself() {
  build
  $BASE_DIR/good-enough -l cpp < doctools/good-enough*.cc | less -r
}

lexer-def() {
  ### Test on a hard Python file

  build
  $BASE_DIR/good-enough -l py < frontend/lexer_def.py | less -r
}

count() {
  wc -l doctools/good-enough* $BASE_DIR/*.h
  echo
  ls -l --si -h $BASE_DIR
}

"$@"

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

readonly -a STRS=(
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

build() {
  local cc=_gen/doctools/good-enough.cc
  local bin=_bin/good-enough

  mkdir -p _gen/doctools
  my-re2c doctools/good-enough.re2c.cc $cc

  local asan='-fsanitize=address'
  #local asan=''

  # gnu99 instead of c99 for fdopen() and getline()
  # g++ - otherwise virtual functions don't work!
  g++ -std=c++11 -O2 -Wall $asan \
    -o $bin $cc

  log "  CXX $cc"

  ls -l $bin 
}

run-tests() {
  local bin=_bin/good-enough

  build

  #$bin 12 '' abc

  #echo
  #$bin "${STRS[@]}"

  echo
  for s in "${STRS[@]}"; do
    echo "==== $s"
    echo "$s" | $bin
    echo
  done

  echo '/dev/null'
  $bin < /dev/null

}

"$@"

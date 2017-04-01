#!/bin/bash
#
# Usage:
#   ./run.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

readonly PY=~/src/Python-3.6.1
readonly DIFF=${DIFF:-diff -u}

parse-with-pgen2() {
  set +o errexit
  for py in "$@"; do
    PYTHONPATH=.. ./parse.py $py >/dev/null #2>&1
    echo $? $py
  done
}

parse-oil() {
  parse-with-pgen2 *.py ../*.py ../osh/*.py ../core/*.py ../asdl/*.py
}

# Parse the old Python2 code
parse-pycompiler2() {
  # parse print statement
  PYTHON2=1 parse-with-pgen2 ~/src/Python-2.7.6/Lib/compiler/*.py
}

# After lib2to3
parse-pycompiler() {
  # parse print statement
  parse-with-pgen2 compiler/*.py
}

clear-tokens() {
  rm token.py tokenize.py
  rm -rf --verbose __pycache ../__pycache__
}

copy-lib2to3() {
  #cp -v $PY/Lib/{token,tokenize}.py .
  #return

  # For comparison
  mkdir -p pgen2

  cp -v $PY/Lib/lib2to3/{pytree,pygram}.py .
  cp -v $PY/Lib/lib2to3/pgen2/{__init__,driver,grammar,parse,token,tokenize,pgen}.py pgen2
  # The 2to3 grammar supports both Python 2 and Python 3.
  # - it has the old print statement.  Well I guess you still want that!  Gah.
  cp -v $PY/Lib/lib2to3/Grammar.txt .
  return

  cp -v $PY/Parser/Python.asdl .

  # For comparison
  #cp -v $PY/Grammar/Grammar .
}

copy-pycompiler() {
  # The last version of the pure Python compile package.
  mkdir -p compiler
  cp -v ~/src/Python-2.7.6/Lib/compiler/*.py compiler
}

# 8700 lines for tokenizer -> tokens -> parser -> homogeneous nodes ->
# transformer -> ast -> compiler -> byte code
count() {
  wc -l *.py pgen2/*.py compiler/*.py | sort -n
}

test-pgen-parse() {
  # Parse itself
  PYTHONPATH=.. ./pgen_parse.py Grammar.txt pgen_parse.py
}

compare-grammar() {
  $DIFF Grammar Grammar.txt
}

# pgen2 has BACKQUOTE = 25.  No main.
compare-tokens() {
  $DIFF token.py pgen2/token.py
}

# This is very different -- is it Python 2 vs. Python 3?
compare-tokenize() {
  $DIFF tokenize.py pgen2/tokenize.py
}

# Features from Python 3 used?  Static types?  I guess Python 3.6 has locals with
# foo: str = 1
# 
# Do I want that?
#
# Main things I ran into were:
# - print statement
# - next() is now __next__ 
# - io.StringIO vs. cStringIO.cstringIO()
#
# And occasional exceptions about encoding.  Had to add .encode('utf-8') in a
# few places.
#
# So mostly cosmetic issues.

test-pgen2() {
  pgen2/pgen.py
}

"$@"

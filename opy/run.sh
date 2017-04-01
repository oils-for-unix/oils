#!/bin/bash
#
# Usage:
#   ./run.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

readonly PY=~/src/Python-3.6.1
readonly DIFF=${DIFF:-diff -u}

_parse-one() {
  PYTHONPATH=. ./parse.py 2to3.grammar parse "$@"
}

_stdlib-parse-one() {
  PYTHONPATH=. ./parse.py 2to3.grammar stdlib-parse "$@"
}

_compile-one() {
  # The production testlist_starexpr is unhandled in the compiler package.
  # Python 2.7 doesn't have it.
  #local g=2to3.grammar 
  local g=py27.grammar
  PYTHONPATH=. ./parse.py $g compile "$@"
}

parse-test() {
  _parse-one testdata/hello_py3.py
  echo ---
  PYTHON2=1 _parse-one testdata/hello_py2.py
}

stdlib-parse-test() {
  _stdlib-parse-one testdata/hello_py3.py
  echo ---
  PYTHON2=1 _stdlib-parse-one testdata/hello_py2.py
}

compile-gold() {
  pushd testdata
  python3 -c 'import hello_py3'

  ls -l __pycache__
  xxd __pycache__/hello_py3.cpython-34.pyc

  popd
}

_compile-and-run() {
  local path=$1
  local basename=$(basename $path .py)

  mkdir -p _tmp
  # Doesn't work why?  Because it was written for Python 2.7?
  local out=_tmp/${basename}.pyc
  _compile-one $path $out

  ls -l $out
  xxd $out

  # Crap, it doesn't work!
  python3 $out

  return

  echo ---
  # This doesn't work because compiler does 'import parser', which is the
  # Python 3 paresr now!
  PYTHON2=1 _compile-one testdata/hello_py2.py
}

compile-hello() {
  _compile-and-run testdata/hello_py3.py
}

compile-self() {
  _compile-and-run ./parse.py
}

old-compile-test() {
  PYTHONPATH=. tools/compile.py testdata/hello_py3.py
}

# 2to3.grammar is from  Python-3.6.1/ Lib/lib2to3/Grammar.txt
parse-with-pgen2() {
  set +o errexit
  for py in "$@"; do
    _parse-one $py >/dev/null #2>&1
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
  parse-with-pgen2 compiler/*.py tools/*.py
}

#
# File Management
#

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

}

# For compatibility with the compiler package.
# I kind of want the static type syntax though?
copy-old-grammar() {
  cp -v $PY27/Grammar/Grammar py27.grammar
}

copy-pycompiler() {
  # The last version of the pure Python compile package.
  mkdir -p compiler
  cp -v ~/src/Python-2.7.6/Lib/compiler/*.py compiler
}

copy-pycompiler-tools() {
  cp -v ~/src/Python-2.7.6/Tools/compiler/{ast.txt,ACKS,README,*.py} tools/
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

readonly PY27=~/src/Python-2.7.6

compare-grammar() {
  # The compiler package was written for a different grammar!
  $DIFF $PY27/Grammar/Grammar 2to3.grammar 
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

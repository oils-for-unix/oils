#!/bin/bash
#
# Usage:
#   ./run.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source compare.sh

readonly PY=$PY36

_parse-one() {
  PYTHONPATH=. ./opy_main.py 2to3.grammar parse "$@"
}

_stdlib-parse-one() {
  PYTHONPATH=. ./opy_main.py 2to3.grammar stdlib-parse "$@"
}

_compile-one() {
  # The production testlist_starexpr is unhandled in the compiler package.
  # Python 2.7 doesn't have it.
  #local g=2to3.grammar 
  local g=py27.grammar
  PYTHONPATH=. ./opy_main.py $g compile "$@"
}

_compile-one-py2() {
  local g=py27.grammar
  PYTHONPATH=. python2 ./opy_main.py $g compile "$@"
}

parse-test() {
  _parse-one testdata/hello_py3.py
  echo ---
  _parse-one testdata/hello_py2.py
}

stdlib-parse-test() {
  _stdlib-parse-one testdata/hello_py3.py
  echo ---
  _stdlib-parse-one testdata/hello_py2.py
}

# Generate .pyc using the Python interpreter.
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

  python3 $out
}

compile-hello() {
  _compile-and-run testdata/hello_py3.py
}

# Bad code object because it only has 14 fields.  Gah!
# We have to marshal the old one I guess.
compile-hello2() {
  local out=_tmp/hello_py2.pyc27
  _compile-one-py2 testdata/hello_py2.py $out
  python $out
}

_compile-many() {
  local version=$1
  shift

  for py in "$@"; do
    echo "--- $py ---"
    local out=_tmp/t.pyc
    if test "$version" = "py2"; then
      _compile-one-py2 $py $out #|| true
    else
      # Caught problem with yield from.  Deletd.
      _compile-one $py $out #|| true
    fi
  done
}

# Problems:
# Can't convert 'bytes' object to str implicitly
compile-opy() {
  local version=${1:-py2}
  _compile-many $version *.py {compiler,pgen2,testdata,tools}/*.py
}

# Has a problem with keyword args after *args, e.g. *args, token=None
compile-osh() {
  local version=${1:-py2}
  # Works
  _compile-many $version ../*.py ../{core,osh,asdl,bin}/*.py
}

# Doesn't work because of compileFile.
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
  parse-with-pgen2 ~/src/Python-2.7.6/Lib/compiler/*.py
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

compare-emitted() {
  # 67 opcodes emitted
  grep emit compiler/pycodegen.py | egrep -o '[A-Z][A-Z_]+' |
    sort | uniq > _tmp/opcodes-emitted.txt

  # 119 ops?
  PYTHONPATH=. python3 > _tmp/opcodes-defined.txt -c '
from compiler import opcode27
names = sorted(opcode27.opmap)
for n in names:
  print(n)
'

  wc -l _tmp/opcodes-defined.txt

  diff -u _tmp/opcodes-{emitted,defined}.txt
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

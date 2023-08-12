#!/usr/bin/env bash
#
# Usage:
#   ./run.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source common.sh
source compare.sh

readonly PY=$PY36

_parse-one() {
  #PYTHONPATH=. ./opy_main.py 2to3.grammar parse "$@"
  opyg parse "$@"
}

parse-test() {
  _parse-one testdata/hello_py3.py  # Python 3 print syntax
  echo ---
  _parse-one testdata/hello_py2.py
}

# It has problems without EOL!
parser-bug() {
  local out=_tmp/opy_parser_bug.py
  echo -n 'foo = {}' > $out
  _parse-one $out
}

_compile-and-run() {
  local path=$1
  local basename=$(basename $path .py)

  mkdir -p _tmp
  local out=_tmp/${basename}.pyc

  #_parse-one $path

  # new opy compile
  _compile-one $path $out
  # unmodified pgen2
  #_compile2-one $path $out

  ls -l $out
  xxd $out

  python $out
}

_stdlib-compile-and-run() {
  local path=$1
  local basename=$(basename $path .py)

  mkdir -p _tmp
  local out=_tmp/${basename}.pyc_stdlib
  misc/stdlib_compile.py $path $out

  ls -l $out
  xxd $out

  python $out
}

stdlib-compile-test() {
  _stdlib-compile-and-run testdata/hello_py2.py
}

# Bad code object because it only has 14 fields.  Gah!
# We have to marshal the old one I guess.
compile-hello2() {
  local out=_tmp/hello_py2.pyc27
  _compile-and-run testdata/hello_py2.py $out
}

# This compiles Python 3 to Python 2 bytecode, and runs it.
compile-hello3() {
  _compile-and-run testdata/hello_py3.py
}

stdlib-determinism() {
  mkdir -p _tmp/det
  local file=./opy_main.py

  # 1 in 10 times we get a diff!  And sometimes same diff!  wtf!
  #
  # Code is definitely reordered.  Basic block.  But then there are tiny byte
  # differences too!

  #local file=./pytree.py
  _stdlib-compile-one $file _tmp/det/$file.1
  _stdlib-compile-one $file _tmp/det/$file.2

  compare-files _tmp/det/$file.{1,2}
}

stdlib-determinism-loop() {
  determinism-loop _stdlib-compile-one 
}

# We want to fix the bug here.  Hm not able to hit it?
compile2-determinism() {
  mkdir -p _tmp/det
  local file=./opy_main.py

  #local file=./pytree.py
  _compile2-one $file _tmp/det/$file.1
  _compile2-one $file _tmp/det/$file.2

  compare-files _tmp/det/$file.{1,2}
}

# Compare stdlib and compile2.  They differ every time!  Is it because somehow
# the Python interpreter is in a different state?  TODO: Could force iteration
# order.

stdlib-compile2() {
  mkdir -p _tmp/det
  local file=./opy_main.py

  #local file=./pytree.py
  _stdlib-compile-one $file _tmp/det/$file.stdlib
  _compile2-one $file _tmp/det/$file.compile2

  compare-files _tmp/det/$file.{stdlib,compile2}
}

export PYTHONHASHSEED=0
#export PYTHONHASHSEED=random

compare-opy-tree() {
  diff -u _tmp/opy-{stdlib,stdlib2}/SIZES.txt || true
  #diff -u _tmp/opy-{stdlib,stdlib2}/MD5.txt || true

  # Hm even two stdlib runs are different!
  # TODO: find the smallest ones that are different

  # Same strings output
  compare-files _tmp/opy-{stdlib,stdlib2}/pytree.pyc
  return
  compare-files _tmp/opy-{stdlib,stdlib2}/opy_main.pyc
  compare-files _tmp/opy-{stdlib,stdlib2}/compiler2/pyassem.pyc
  compare-files _tmp/opy-{stdlib,stdlib2}/compiler2/pycodegen.pyc
  compare-files _tmp/opy-{stdlib,stdlib2}/compiler2/symbols.pyc
  compare-files _tmp/opy-{stdlib,stdlib2}/compiler2/transformer.pyc
  return

  #diff -u _tmp/opy-{stdlib,compile2}/MANIFEST.txt

  compare-files _tmp/opy-{stdlib,compile2}/util.pyc
  compare-files _tmp/opy-{stdlib,compile2}/pgen2/driver.pyc
  compare-files _tmp/opy-{stdlib,compile2}/opy_main.pyc
}

compare-osh-tree() {
  #diff -u _tmp/opy-{stdlib,stdlib2}/SIZES.txt || true
  #compare-files _tmp/osh-{ccompile,compile2}/core/id_kind_test.pyc
  compare-files _tmp/osh-{ccompile,compile2}/core/testdbg.pyc
}

unit-osh() {
  local dir=${1:-_tmp/osh-stdlib}
  local vm=${2:-byterun}  # or cpython
  shift 2
  pushd $dir
  if test $vm = byterun; then
    PYTHONPATH=. byterun -c "$@"
  else
    PYTHONPATH=. python "$@"
  fi
  popd
}

# Combinations of {ccompile, compiler2} x {cpython, byterun}
compile-run-one() {
  local compiler=${1:-ccompile}  # or compile2
  local vm=${2:-byterun}  # or cpython
  local py=$3
  shift 3

  if ! { test $compiler = ccompile || test $compiler = compile2; } then
    die "Invalid compiler $compiler"
  fi

  local dir="_tmp/osh-$compiler"
  local pyc="$dir/$(basename $py)c"
  _$compiler-one $py $pyc

  export PYTHONPATH=$dir 
  if test $vm = cpython; then
    python $pyc "$@"
  elif test $vm = byterun; then
    #byterun -v -c $pyc "$@" 
    byterun -c $pyc "$@" 
  else
    die $vm
  fi
}

compare-sizes() {
  local left=$1
  local right=$2
  find $left -name '*.pyc' -a -printf '%s %P\n' | sort -n
  echo ---
  # Wow, opyc files are bigger!  Code is not as optimal or what?
  # Order is roughly the same.
  find $right -name '*.opyc' -a -printf '%s %P\n' | sort -n
}

compare-opy-sizes() {
  compare-sizes .. _tmp/opy
}

compare-osh-sizes() {
  # TODO: filter opy out of the left
  compare-sizes .. _tmp/osh
}

# Doesn't work because of compileFile.
old-compile-test() {
  PYTHONPATH=. tools/compile.py testdata/hello_py3.py
}

#
# Parsing tests subsummed by compiling
#

# 2to3.grammar is from  Python-3.6.1/ Lib/lib2to3/Grammar.txt
parse-with-pgen2() {
  set +o errexit
  for py in "$@"; do
    _parse-one $py >/dev/null #2>&1
    echo $? $py
  done
}

# This fails due to some files not using __future__ print_function.
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
  mkdir -p compiler2
  cp -v ~/src/Python-2.7.6/Lib/compiler/*.py compiler2
}

copy-pycompiler-tools() {
  cp -v ~/src/Python-2.7.6/Tools/compiler/{ast.txt,ACKS,README,*.py} tools/
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

"$@"

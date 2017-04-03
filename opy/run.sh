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

parse-test() {
  _parse-one testdata/hello_py3.py
  echo ---
  _parse-one testdata/hello_py2.py
}

_stdlib-parse-one() {
  PYTHONPATH=. ./opy_main.py 2to3.grammar stdlib-parse "$@"
}

stdlib-parse-test() {
  _stdlib-parse-one testdata/hello_py3.py
  echo ---
  _stdlib-parse-one testdata/hello_py2.py
}

_compile-one() {
  # The production testlist_starexpr is unhandled in the compiler package.
  # Python 2.7 doesn't have it.
  #local g=2to3.grammar 
  local g=py27.grammar
  PYTHONPATH=. ./opy_main.py $g compile "$@"
}

_stdlib-compile-one() {
  misc/stdlib_compile.py "$@"
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
  local out=_tmp/${basename}.pyc
  _compile-one $path $out

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

_compile-many() {
  local version=$1
  shift

  for py in "$@"; do
    echo "--- $py ---"
    local out=_tmp/t.pyc
    _compile-one $py $out #|| true
  done
}

compile-opy() {
  local version=${1:-py2}
  _compile-many $version *.py {compiler,pgen2,testdata,tools}/*.py
}

compile-osh() {
  local version=${1:-py2}
  # Works
  _compile-many $version ../*.py ../{core,osh,asdl,bin}/*.py
}

_compile-tree() {
  local src_tree=$1
  local dest_tree=$2
  local version=$3
  shift 3

  #local ext=opyc

  rm -r -f $dest_tree

  local ext=pyc

  for rel_path in "$@"; do
    echo $rel_path
    local dest=${dest_tree}/${rel_path%.py}.${ext}
    mkdir -p $(dirname $dest)

    if test $version = stdlib; then
      _stdlib-compile-one $src_tree/${rel_path} $dest
    else
      _compile-one $src_tree/${rel_path} $dest
    fi
  done

  tree $dest_tree
  md5-manifest $dest_tree
}

md5-manifest() {
  local tree=$1
  pushd $tree
  find . -type f | sort | xargs md5sum | tee MANIFEST.txt
  popd
}

compile-opy-tree() {
  local src=$PWD
  local files=( $(find $src -name _tmp -a -prune -o -name '*.py' -a -printf '%P\n') )

  local dest=_tmp/opy-opy/ 
  _compile-tree $src $dest opy "${files[@]}"

  local dest=_tmp/opy-stdlib/ 
  _compile-tree $src $dest stdlib "${files[@]}"
}

compile-osh-tree() {
  local src=$(cd .. && echo $PWD)
  local files=( $(find $src \
              -name _tmp -a -prune -o \
              -name opy -a -prune -o \
              -name tests -a -prune -o \
              -name '*.py' -a -printf '%P\n') )

  _compile-tree $src _tmp/osh-opy/ opy "${files[@]}"
  _compile-tree $src _tmp/osh-stdlib/ stdlib "${files[@]}"
}

byterun() {
  ~/git/other/byterun/byterun/__main__.py "$@"
}

# Wow!  Runs itself to parse itself... I need some VM instrumentation to make
# sure it's not accidentally cheating or leaking.
opy-parse-on-byterun() {
  local g=$PWD/2to3.grammar 
  local arg=$PWD/opy_main.py
  pushd _tmp/opy-stdlib
  byterun -c opy_main.pyc $g parse $arg
  popd
}

osh-parse-on-byterun() {
  cmd=(osh --ast-output - --no-exec -c 'echo "hello world"')

  ../bin/oil.py "${cmd[@]}"

  cp ../osh/osh.asdl _tmp/osh-stdlib/osh
  cp ../core/runtime.asdl _tmp/osh-stdlib/core

  echo ---

  byterun -c _tmp/osh-stdlib/bin/oil.pyc "${cmd[@]}"
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

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

_compile2-one() {
  local g=py27.grammar
  PYTHONPATH=. ./opy_main.py $g compile2 "$@"
}

_stdlib-compile-one() {
  # Run it from source, so we can patch.  Bug still appears.

  #$PY27/python misc/stdlib_compile.py "$@"

  # No with statement
  #~/src/Python-2.4.6/python misc/stdlib_compile.py "$@"

  # NOT here
  #~/src/Python-2.6.9/python misc/stdlib_compile.py "$@"

  # Bug appears in Python 2.7.9 too!
  #~/src/Python-2.7.9/python misc/stdlib_compile.py "$@"

  # Why is it in 2.7.2?  No hash randomization there?
  #~/src/Python-2.7.2/python misc/stdlib_compile.py "$@"

  # Woah it took 51 iterations to find!
  # Much rarer in Python 2.7.0.  100 iterations didn't find it?
  # Then 35 found it.  Wow.
  ~/src/Python-2.7/python misc/stdlib_compile.py "$@"

  #misc/stdlib_compile.py "$@"
}

_ccompile-one() {
  misc/ccompile.py "$@"
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

determinism-loop() {
  local func=$1
  local file=./opy_main.py

  for i in $(seq 100); do
    echo "--- $i ---"
    $func $file _tmp/det/$file.1
    $func $file _tmp/det/$file.2

    local size1=$(stat --format '%s' _tmp/det/$file.1)
    local size2=$(stat --format '%s' _tmp/det/$file.2)
    if test $size1 != $size2; then
      compare-files _tmp/det/$file.{1,2}
      echo "Found problem after $i iterations"
      break
    fi
  done
}

stdlib-determinism-loop() {
  determinism-loop _stdlib-compile-one 
}

compile2-determinism-loop() {
  determinism-loop _compile2-one 
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

_compile-tree() {
  local src_tree=$1
  local dest_tree=$2
  local version=$3
  shift 3

  rm -r -f $dest_tree

  #local ext=opyc
  local ext=pyc

  for rel_path in "$@"; do
    echo $rel_path
    local dest=${dest_tree}/${rel_path%.py}.${ext}
    mkdir -p $(dirname $dest)

    if test $version = stdlib; then
      _stdlib-compile-one $src_tree/${rel_path} $dest
    elif test $version = compiler2; then
      _compile2-one $src_tree/${rel_path} $dest
    elif test $version = ccompile; then
      _ccompile-one $src_tree/${rel_path} $dest
    elif test $version = opy; then
      _compile-one $src_tree/${rel_path} $dest
    else
      die "bad"
    fi
  done

  tree $dest_tree
  md5-manifest $dest_tree
}

export PYTHONHASHSEED=0
#export PYTHONHASHSEED=random

md5-manifest() {
  local tree=$1
  pushd $tree
  # size and name
  find . -type f | sort | xargs stat --format '%s %n' | tee SIZES.txt
  find . -type f | sort | xargs md5sum | tee MD5.txt
  popd
}

compile-opy-tree() {
  local src=$PWD
  local files=( $(find $src \
              -name _tmp -a -prune -o \
              -name '*.py' -a -printf '%P\n') )

  local dest=_tmp/opy-compile2/ 
  _compile-tree $src $dest compiler2 "${files[@]}"

  local dest=_tmp/opy-stdlib/ 
  _compile-tree $src $dest stdlib "${files[@]}"
}

# For comparing different bytecode.
compare-files() {
  local left=$1
  local right=$2

  md5sum "$@"
  ls -l "$@"

  misc/inspect_pyc.py $left > _tmp/pyc-left.txt
  misc/inspect_pyc.py $right > _tmp/pyc-right.txt
  $DIFF _tmp/pyc-{left,right}.txt || true

  return
  strings $left > _tmp/str-left.txt
  strings $right > _tmp/str-right.txt

  # The ORDER of strings is definitely different.  But the SIZE and CONTENTS
  # are too!
  # Solution: can you walk your own code objects and produce custom .pyc files?

  diff -u _tmp/str-{left,right}.txt || true

  #xxd $left > _tmp/hexleft.txt
  #xxd $right > _tmp/hexright.txt
  #diff -u _tmp/hex{left,right}.txt || true
  echo done
}

compare-opy-tree() {
  diff -u _tmp/opy-{stdlib,stdlib2}/SIZES.txt || true
  #diff -u _tmp/opy-{stdlib,stdlib2}/MD5.txt || true

  # Hm even two stdlib runs are different!
  # TODO: find the smallest ones that are differet

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

compile-osh-tree() {
  local src=$(cd .. && echo $PWD)
  local files=( $(find $src \
              -name _tmp -a -prune -o \
              -name opy -a -prune -o \
              -name tests -a -prune -o \
              -name '*.py' -a -printf '%P\n') )

  _compile-tree $src _tmp/osh-ccompile/ ccompile "${files[@]}"
  _compile-tree $src _tmp/osh-stdlib/ stdlib "${files[@]}"
  _compile-tree $src _tmp/osh-compile2/ compiler2 "${files[@]}"
}

fill-osh-tree() {
  local dir=${1:-_tmp/osh-stdlib}
  cp -v ../osh/osh.asdl $dir/osh
  cp -v ../core/runtime.asdl $dir/core
  cp -v ../asdl/arith.asdl $dir/asdl
  ln -v -s -f $PWD/../core/libc.so $dir/core
}

# TODO: Run all cross product of {compile2,compile} x {byterun,cpython}.

test-osh-tree() {
  local dir=${1:-_tmp/osh-stdlib}
  local vm=${2:-byterun}  # byterun or cpython

  pushd $dir
  mkdir -p _tmp
  for t in {asdl,core,osh}/*_test.pyc; do
    if [[ $t == *arith_parse_test.pyc ]]; then
      continue
    fi
    #if [[ $t == *libc_test.pyc ]]; then
    #  continue
    #fi

    echo $t
    if test $vm = byterun; then
      PYTHONPATH=. byterun -c $t
    else
      PYTHONPATH=. python $t
    fi
  done
  popd
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

# Compile and byterun

# Weird interaction:
#
# ccompile / run std VM -- OK
# ccompile / byterun VM -- OK
# stdlib-compiler or compile2 / run with std VM -- OK
#
# stdlib-compiler or compiler2 / byterun VM -- weird exception!
#
# So each component works with the python VM, but not with each other.
#
# Oh you don't have a method of compling with the python VM.  Then run with
# byterun.  That would be a good comparison.

pyc-byterun() {
  local t=${1:-core/id_kind_test.py}
  pushd ..

  python -c 'from core import id_kind_test' || true
  ls -l ${t}c

  PYTHONPATH=. byterun -c ${t}c
  popd
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
  mkdir -p compiler2
  cp -v ~/src/Python-2.7.6/Lib/compiler/*.py compiler2
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

determinism() {
  # This changes it.  Python 2.7 doesn't have it on by default I guess.
  # So what is the cause in the compiler package?
  #export PYTHONHASHSEED=random

  misc/determinism.py > _tmp/d1.txt
  misc/determinism.py > _tmp/d2.txt
  $DIFF _tmp/{d1,d2}.txt && echo SAME
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

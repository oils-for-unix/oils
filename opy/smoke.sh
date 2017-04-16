#!/bin/bash
#
# Smoke tests for OPy.
#
# Usage:
#   ./smoke.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source common.sh

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

md5-manifest() {
  local tree=$1
  pushd $tree
  # size and name
  find . -type f | sort | xargs stat --format '%s %n' | tee SIZES.txt
  find . -type f | sort | xargs md5sum | tee MD5.txt
  popd
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

byterun-speed-test() {
  cat >_tmp/speed.py <<EOF
import sys 
n = int(sys.argv[1])
sum = 0
for i in xrange(n):
  sum += i
print(sum)
EOF

  _compile2-one _tmp/speed.py _tmp/speed.pyc
  cp _tmp/speed.pyc _tmp/speed.opyc

  # 7 ms
  echo PYTHON
  time python _tmp/speed.opyc 10000

  # 205 ms.  So it's 30x slower.  Makes sense.
  echo BYTERUN
  time byterun -c _tmp/speed.opyc 10000
}

# Wow!  Runs itself to parse itself... I need some VM instrumentation to make
# sure it's not accidentally cheating or leaking.
opy-parse-on-byterun() {
  local g=$PWD/2to3.grammar 
  local arg=$PWD/opy_main.py
  pushd _tmp/opy-compile2
  byterun -c opy_main.pyc $g parse $arg
  popd
}

osh-parse-on-byterun() {
  cmd=(osh --ast-output - --no-exec -c 'echo "hello world"')

  ../bin/oil.py "${cmd[@]}"
  echo ---
  byterun -c _tmp/osh-compile2/bin/oil.pyc "${cmd[@]}"
}

"$@"

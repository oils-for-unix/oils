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

  #local dest=_tmp/opy-compile2/ 
  #_compile-tree $src $dest compiler2 "${files[@]}"
  #local dest=_tmp/opy-stdlib/ 
  #_compile-tree $src $dest stdlib "${files[@]}"

  _compile-tree $src _tmp/opy-ccompile/ ccompile "${files[@]}"
  _compile-tree $src _tmp/opy-opy/ opy "${files[@]}"
}

compile-osh-tree() {
  local src=$(cd .. && echo $PWD)
  local files=( $(find $src \
              -name _tmp -a -prune -o \
              -name opy -a -prune -o \
              -name tests -a -prune -o \
              -name '*.py' -a -printf '%P\n') )

  _compile-tree $src _tmp/osh-ccompile/ ccompile "${files[@]}"
  _compile-tree $src _tmp/osh-opy/ opy "${files[@]}"

  #_compile-tree $src _tmp/osh-compile2/ compiler2 "${files[@]}"

  # Not deterministic!
  #_compile-tree $src _tmp/osh-compile2.gold/ compiler2 "${files[@]}"
  #_compile-tree $src _tmp/osh-stdlib/ stdlib "${files[@]}"
}

fill-osh-tree() {
  local dir=${1:-_tmp/osh-stdlib}
  cp -v ../osh/osh.asdl $dir/osh
  cp -v ../core/runtime.asdl $dir/core
  cp -v ../asdl/arith.asdl $dir/asdl
  ln -v -s -f $PWD/../core/libc.so $dir/core
}

test-osh-tree() {
  local dir=${1:-_tmp/osh-opy}
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
      PYTHONPATH=. opy_ run $t
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

#
# Byterun smoke tests
#

# Wow!  Runs itself to parse itself... I need some VM instrumentation to make
# sure it's not accidentally cheating or leaking.
opy-parse-on-byterun() {
  #local arg=$PWD/opy_main.py
  local arg=$PWD/testdata/hello_py2.py
  pushd _tmp/opy-opy
  opy_ run opy_main.pyc $GRAMMAR parse $arg
  popd
}

osh-parse-on-byterun() {
  cmd=(osh --ast-output - --no-exec -c 'echo "hello world"')

  ../bin/oil.py "${cmd[@]}"
  echo ---
  opy_ run _tmp/osh-opy/bin/oil.pyc "${cmd[@]}"
}

opy-hello2() {
  opy_ run testdata/hello_py2.py
}

opy-hello3() {
  opy_ run testdata/hello_py3.py
}

#
# Determinism
#
# There are problems here, but it's because of an underlying Python 2.7 issue.
# For now we will do functional tests.
#

# Doesn't suffice for for compiler2 determinism.
#export PYTHONHASHSEED=0

inspect-pyc() {
  PYTHONPATH=. misc/inspect_pyc.py "$@"
}

# For comparing different bytecode.
compare-bytecode() {
  local left=$1
  local right=$2

  md5sum "$@"
  ls -l "$@"

  inspect-pyc $left > _tmp/pyc-left.txt
  inspect-pyc $right > _tmp/pyc-right.txt
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

# Compile opy_main a 100 times and make sure it's the same.
#
# NOTE: This doesn't surface all the problems.  Remember the fix was in
# compiler2/misc.py:Set.
determinism-loop() {
  local func=$1
  local file=${2:-./opy_main.py}

  mkdir -p _tmp/det

  local name=$(basename $file)
  for i in $(seq 100); do
    echo "--- $i ---"
    $func $file _tmp/det/$name.1
    $func $file _tmp/det/$name.2

    local size1=$(stat --format '%s' _tmp/det/$name.1)
    local size2=$(stat --format '%s' _tmp/det/$name.2)
    if test $size1 != $size2; then
      # TODO: Import from run.sh
      compare-bytecode _tmp/det/$file.{1,2}
      echo "Found problem after $i iterations"
      break
    fi
  done
}

compile2-determinism-loop() {
  determinism-loop _compile2-one ../core/lexer.py
}

if test $(basename $0) = 'smoke.sh'; then
  "$@"
fi

#!/usr/bin/env bash
#
# Smoke tests for OPy.
#
# Usage:
#   ./smoke.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source common.sh
source compare.sh  # for DIFF

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

_fill-opy-tree() {
  echo TODO: grammar pickle
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

make-links() {
  local dir=${1:-_tmp/osh-opy}

  local run=$PWD/../scripts/run.sh 

  pushd $dir
  $run make-pyc-links
  popd
  #tree $dir
}

_fill-osh-tree() {
  local dir=${1:-_tmp/osh-opy}
  cp -v ../osh/{osh,types}.asdl $dir/osh
  cp -v ../core/runtime.asdl $dir/core
  cp -v ../asdl/arith.asdl $dir/asdl
  ln -v -s -f $PWD/../{libc,fastlex}.so $dir

  # Needed for help text.
  ln -v -s -f --no-target-directory $PWD/../_build $dir/_build

  make-links $dir
}

osh-opy() {
  python _tmp/osh-opy/bin/osh "$@"
}

test-help() {
  osh-opy --help
}

# Compile with both compile() and OPy.
# TODO:
# - What about the standard library?  The whole app bundle should be
# compiled with OPy.
# - This could be part of the Travis build.  It will ensure no Python 2
# print statements sneak in.
compile-osh-tree() {
  local src=$(cd .. && echo $PWD)

  # NOTE: Exclude _devbuild/cpython-full, but include _devbuild/gen.
  local files=( $(find $src \
              -name _tmp -a -prune -o \
              -name _chroot -a -prune -o \
              -name cpython-full -a -prune -o \
              -name _deps -a -prune -o \
              -name Python-2.7.13 -a -prune -o \
              -name opy -a -prune -o \
              -name 'test' -a -prune -o \
              -name '*.py' -a -printf '%P\n') )

  _compile-tree $src _tmp/osh-ccompile/ ccompile "${files[@]}"
  _compile-tree $src _tmp/osh-opy/ opy "${files[@]}"

  _fill-osh-tree _tmp/osh-ccompile/ 
  _fill-osh-tree _tmp/osh-opy/

  #_compile-tree $src _tmp/osh-compile2/ compiler2 "${files[@]}"

  # Not deterministic!
  #_compile-tree $src _tmp/osh-compile2.gold/ compiler2 "${files[@]}"
  #_compile-tree $src _tmp/osh-stdlib/ stdlib "${files[@]}"
}

zip-oil-tree() {
  #pushd _tmp/osh-opy
  rm -f _tmp/oil.zip
  pushd _tmp/osh-ccompile
  zip ../oil.zip -r .
  popd
}

# TODO:
# - Run with oil.ovm{,-dbg}
test-unit() {
  local dir=${1:-_tmp/osh-opy}
  local vm=${2:-cpython}  # byterun or cpython

  pushd $dir
  mkdir -p _tmp
  #for t in {build,test,native,asdl,core,osh,test,tools}/*_test.py; do
  for t in {asdl,core,osh}/*_test.pyc; do

    echo $t
    if test $vm = byterun; then
      PYTHONPATH=. opy_ run $t
    elif test $vm = cpython; then
      PYTHONPATH=. python $t
    else
      die "Invalid VM $vm"
    fi
  done
  popd
}

test-osh-smoke() {
  local dir=${1:-_tmp/osh-opy}
  local vm=${2:-cpython}  # byterun or cpython
}

write-speed() {
  cat >_tmp/speed.py <<EOF
def do_sum(n):
  sum = 0
  for i in xrange(n):
    sum += i
  print(sum)

if __name__ == '__main__':
  import sys
  n = int(sys.argv[1])
  do_sum(n)

EOF
  cat >_tmp/speed_main.py <<EOF
import sys 
import speed

n = int(sys.argv[1])
speed.do_sum(n)
EOF
}

opy-speed-test() {
  write-speed

  _compile-one _tmp/speed.py _tmp/speed.pyc
  _compile-one _tmp/speed_main.py _tmp/speed_main.pyc

  cp _tmp/speed.pyc _tmp/speed.opyc

  # For logging
  local n=10000
  #local n=10

  # 7 ms
  echo PYTHON
  time python _tmp/speed.opyc $n

  # 205 ms.  So it's 30x slower.  Makes sense.
  echo OPY
  time opy_ run _tmp/speed.opyc $n

  # 7 ms
  echo PYTHON
  time python _tmp/speed_main.pyc $n

  # 205 ms.  So it's 30x slower.  Makes sense.
  echo OPY
  time opy_ run _tmp/speed_main.pyc $n
}

byterun-speed-test() {
  write-speed

  echo OLD BYTERUN
  time _byterun $PWD/_tmp/speed_main.py 10000
  time _byterun $PWD/_tmp/speed.py 10000
}


_byterun() {
  # Wow this is SO confusing.
  # Not executable on master branch

  #python ~/git/other/byterun/byterun/__main__.py "$@"
  #python ~/git/other/byterun/byterun "$@"
  #python -m ~/git/other/byterun/byterun "$@"
  #PYTHONPATH=~/git/other/byterun 

  # WHY is this the only way to make it work?
  pushd ~/git/other/byterun 
  python -m byterun.__main__ "$@"
  popd
}

#
# Byterun smoke tests
#

# Wow!  Runs itself to parse itself... I need some VM instrumentation to make
# sure it's not accidentally cheating or leaking.
opy-parse-on-byterun() {
  local arg=$PWD/testdata/hello_py2.py
  pushd _tmp/opy-opy
  opyg run opy_main.pyc -g $GRAMMAR parse $arg
  popd
}

osh-parse-on-byterun() {
  cmd=(osh --ast-output - --no-exec -c 'echo "hello world"')

  ../bin/oil.py "${cmd[@]}"
  echo ---
  opyg run _tmp/osh-opy/bin/oil.pyc "${cmd[@]}"
}

opy-hello2() {
  opyg run testdata/hello_py2.py
}

opy-hello3() {
  opyg run testdata/hello_py3.py
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

# Compile opy_ a 100 times and make sure it's the same.
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
      echo "mismatched sizes: $size1 $size2"
      # TODO: Import from run.sh
      compare-bytecode _tmp/det/$name.{1,2}
      echo "Found problem after $i iterations"
      break
    fi
  done
}

opy-determinism-loop() {
  determinism-loop _compile-one ../core/lexer.py
}

# Not able to reproduce the non-determinism with d.keys()?  Why not?
hash-determinism() {
  local in=$1
  local out=$2
  # This changes it.  Python 2.7 doesn't have it on by default I guess.
  # So what is the cause in the compiler package?
  #export PYTHONHASHSEED=random

  misc/determinism.py $in > $out
}

hash-determinism-loop() {
  determinism-loop hash-determinism
}

if test $(basename $0) = 'smoke.sh'; then
  "$@"
fi

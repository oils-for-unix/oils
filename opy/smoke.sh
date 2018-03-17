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

zip-oil-tree() {
  #pushd _tmp/osh-opy
  rm -f _tmp/oil.zip
  pushd _tmp/osh-ccompile
  zip ../oil.zip -r .
  popd
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

# For comparing different bytecode.
compare-bytecode() {
  local left=$1
  local right=$2

  md5sum "$@"
  ls -l "$@"

  opyc-dis $left > _tmp/pyc-left.txt
  opyc-dis $right > _tmp/pyc-right.txt
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

    opyc-dis-md5 _tmp/det/$name.{1,2} | tee _tmp/det/md5.txt
    awk '
    NR == 1 { left = $2 } 
    NR == 2 { right = $2 } 
    END     { if (NR != 2) {
                print "Expected two rows, got " NR
                exit(1)
              }
              if (left != right) { 
                print "FATAL: .pyc files are different!"
                exit(1)
              }
            }
    ' _tmp/det/md5.txt
    local status=$?

    if test $status != 0; then
      compare-bytecode _tmp/det/$name.{1,2}
      echo "Found problem after $i iterations"
      break
    fi

    #local size1=$(stat --format '%s' _tmp/det/$name.1)
    #local size2=$(stat --format '%s' _tmp/det/$name.2)

    #if test $size1 != $size2; then
    #  echo "mismatched sizes: $size1 $size2"
    #  # TODO: Import from run.sh
    #  compare-bytecode _tmp/det/$name.{1,2}
    #  echo "Found problem after $i iterations"
    #  break
    #fi
  done
}

opyc-compile() { ../bin/opyc compile "$@"; }
opyc-dis() { ../bin/opyc dis "$@"; }
opyc-dis-md5() { ../bin/opyc dis-md5 "$@"; }
stdlib-compile() { misc/stdlib_compile.py "$@"; }

# FAILS
opy-determinism-loop() {
  #local file=../core/lexer.py
  local file=../core/word_compile.py  # FIXED
  #local file=../Python-2.7.13/Lib/genericpath.py
  determinism-loop opyc-compile $file
}

# FAILS
stdlib-determinism-loop() {
  #local file=../core/lexer.py
  local file=../core/word_compile.py  # flanders has issue
  determinism-loop stdlib-compile $file
}

# BUG: FlowGraph flattening was non-deterministic.  It's a graph that is
# correct in several orders.  See order_blocks() in pyassem.py.

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

rebuild-and-md5() {
  cd ..
  make clean-repo
  make _build/opy/py27.grammar.pickle
  make _bin/oil.ovm-dbg
  local out=_tmp/pyc-md5.txt
  build/metrics.sh pyc-md5 | sort -n | tee $out

  log ""
  log "Wrote $out"
}

copy-left-right() {
  local src=flanders.local:~/git/oilshell/oil
  mkdir -p _tmp/flanders _tmp/lisa
  scp $src/_build/oil/bytecode-opy.zip $src/_tmp/pyc-md5.txt _tmp/flanders
  src=..
  cp -v $src/_build/oil/bytecode-opy.zip $src/_tmp/pyc-md5.txt _tmp/lisa
}

diff-left-right() {
  if diff _tmp/{lisa,flanders}/pyc-md5.txt; then
    echo SAME
  else
    echo DIFFERENT
  fi
}

unzip-left-right() {
  for host in lisa flanders; do
    pushd _tmp/$host
    unzip bytecode-opy.zip core/word_compile.pyc
    popd
  done
}

diff-one-left-right() {
  for host in lisa flanders; do
    opyc-dis _tmp/$host/core/word_compile.pyc > _tmp/$host/word_compile.dis
  done
  diff -u _tmp/{lisa,flanders}/word_compile.dis
}

if test $(basename $0) = 'smoke.sh'; then
  "$@"
fi

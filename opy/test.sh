#!/bin/bash
#
# Usage:
#   ./test.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

readonly THIS_DIR=$(cd $(dirname $0) && pwd)

source $THIS_DIR/common.sh

# We have to invoke opyc like this because byterun uses __import__, which
# respects PYTHONPATH.  If we use ../bin/opyc, it will use the CPython-compiled
# bytecode in the repo, rather than the OPy-compiled bytecode in _tmp/oil-opy.
opyc() {
  python bin/opy_.pyc opyc "$@"
}

oil-opy() {
  _tmp/oil-opy/bin/oil "$@"
}

# TODO:
# - Run with oil.ovm{,-dbg}

# 3/2018 byterun results:
#
# Ran 28 tests, 4 failures
# asdl/arith_parse_test.pyc core/glob_test.pyc core/lexer_gen_test.pyc osh/lex_test.pyc
#

oil-unit() {
  local dir=${1:-_tmp/repo-with-opy}
  local vm=${2:-cpython}  # byterun or cpython

  pushd $dir

  #$OPYC run core/cmd_exec_test.pyc

  local n=0
  local -a failures=()

  # TODO: Share with test/unit.sh.
  #for t in {build,test,native,asdl,core,osh,test,tools}/*_test.py; do
  for t in {asdl,core,frontend,osh,oil_lang}/*_test.pyc; do

    echo $t
    if test $vm = byterun; then

      set +o errexit
      set +o nounset  # for empty array!

      # Note: adding PYTHONPATH screws things up, I guess because it's the HOST
      # interpreter pythonpath.
      opyc run $t
      status=$?

      if test $status -ne 0; then
        failures=("${failures[@]}" $t)
      fi
      (( n++ ))

    elif test $vm = cpython; then
      PYTHONPATH=. python $t
      #(( n++ ))

    else
      die "Invalid VM $vm"
    fi
  done
  popd

  if test $vm = byterun; then
    echo "Ran $n tests, ${#failures[@]} failures"
    echo "${failures[@]}"
  fi
}

oil-unit-byterun() {
  oil-unit '' byterun
}

readonly -a FAILED=(
  asdl/demo_asdl_test.pyc
)

oil-byterun-failed() {
  #set +o errexit

  for t in "${FAILED[@]}"; do

    echo
    echo ---
    echo --- $t
    echo ---

    pushd _tmp/repo-with-opy
    opyc run $t
    popd
  done
}

byterun-unit() {
  pushd $THIS_DIR/..
  for t in opy/byterun/test_*.py; do
    echo
    echo "*** $t"
    echo
    PYTHONPATH=. $t
  done
  popd
}


# TODO: Fix this!
opy-unit() {
 for t in compiler2/*_test.py; do
   echo $t
   $t
 done
}

# Isolated failures.

# File "/home/andy/git/oilshell/oil/bin/../opy/byterun/pyvm2.py", line 288, in manage_block_stack
#   block = self.frame.block_stack[-1]
# IndexError: list index out of range

generator-exception() {
  testdata/generator_exception.py
  ../bin/opyc run testdata/generator_exception.py 
}

generator-exception-diff() {
  rm -f -v testdata/generator_exception.pyc
  testdata/generator_exception.py

  pushd testdata 
  python -c 'import generator_exception'
  popd

  echo ---
  ../bin/opyc compile testdata/generator_exception.py _tmp/ge-opy.pyc

  ../bin/opyc dis testdata/generator_exception.pyc > _tmp/ge-cpython.txt
  ../bin/opyc dis _tmp/ge-opy.pyc > _tmp/ge-opy.txt

  diff -u _tmp/ge-{cpython,opy}.txt
}

# TypeError: unbound method append() must be called with SubPattern instance as
# first argument (got tuple instance instead) 

regex-compile() {
  testdata/regex_compile.py
  echo ---
  ../bin/opyc run testdata/regex_compile.py
}

re-dis() {
  ../bin/opyc dis /usr/lib/python2.7/sre_parse.pyc
}

# Spec tests under byterun.
spec() { 
  local action=$1  # e.g. 'smoke' or 'all'
  shift

  pushd $THIS_DIR/..

  # TODO: Should be OSH_ALT instead of OSH_OVM?
  # Usually it is dev build vs. release build, but here it is CPython vs.
  # byterun.

  # HACK to get around __import__ problem with byterun.

  OSH_LIST="bin/osh $OSH_BYTERUN" test/spec.sh $action "$@"
  popd
}

# The way to tickle the 'import' bug.  We need to wrap SOME functions in
# pyobj.Function.  Otherwise it will run too fast!

opy-speed-test() {
  opyc-compile testdata/speed.py _tmp/speed.pyc
  opyc-compile testdata/speed_main.py _tmp/speed_main.pyc

  cp _tmp/speed.pyc _tmp/speed.opyc

  # For logging
  local n=10000
  #local n=10

  # 7 ms
  echo PYTHON
  time python _tmp/speed.opyc $n

  # 205 ms.  So it's 30x slower.  Makes sense.
  echo OPY
  time opyc-run _tmp/speed.opyc $n

  #
  # byterun Import bug regression test!
  #

  # 7 ms
  echo PYTHON
  time python _tmp/speed_main.pyc $n

  # 205 ms.  So it's 30x slower.  Makes sense.
  echo OPY
  time opyc-run _tmp/speed_main.pyc $n
}

# Compare execution.
# Although some of these are mostly there for disassembly.
gold() {
  set +o errexit
  for script in gold/*.py; do

    $script > _tmp/gold-cpython.txt 2>&1

    # As a test, disable LOAD_FAST, etc.  The output should still be the same.
    ../bin/opyc run -fast-ops=0 $script > _tmp/gold-opy-byterun.txt 2>&1

    if diff -u _tmp/gold-{cpython,opy-byterun}.txt; then
      echo "OK $script"
    else
      echo "FAIL $script"
      return 1
    fi
  done
}

compile-with-cpython() {
  local path=${1:-gold/with_statement.py}
  local pyc=${path}c
  rm --verbose -f $pyc
  pushd $(dirname $path)
  python -c "import $(basename $path .py)"
  popd
  ls -l $pyc

  ../bin/opyc dis $pyc
}

# Print something 99 parentheses deep!  It causes a MemoryError in the parser,
# but 98 doesn't.  I noticed MAXSTACK = 1500 in Parser/parser.h.
pgen-stack() {
  python -c '
import sys
n = int(sys.argv[1])
print "(" * n
print "42"
print ")" * n
' 99 > _tmp/deep.py

  python _tmp/deep.py
}

if test $(basename $0) = 'test.sh'; then
  "$@"
fi

#!/usr/bin/env bash
#
# Test osh usage "from the outside".
#
# Usage:
#   test/osh-usage.sh <function name>

: ${LIB_OSH=stdlib/osh}
source $LIB_OSH/bash-strict.sh
source $LIB_OSH/no-quotes.sh

source test/common.sh  # run-test-funcs

DISABLED-test-oheap() {
  # OHeap was disabled
  if bin/osh -n --ast-format oheap -c 'echo hi'; then
    die "Should have failed"
  fi
  echo OK
}

test-ast-formats() {
  bin/osh -n -c 'echo hi'
  bin/osh -n --ast-format text -c 'echo hi'
  bin/osh -n --ast-format abbrev-html -c 'echo hi'
  bin/osh -n --ast-format html -c 'echo hi'

  # Removed with oheap
  return
  local ast_bin=_tmp/smoke-ast.bin 
  bin/osh -n --ast-format oheap -c 'echo hi' > $ast_bin
  ls -l $ast_bin
  hexdump -C $ast_bin
}

# Read from a file.
test-osh-file() {
  echo ===== Hello
  cat >_tmp/smoke-prog.sh <<EOF
echo hi

myfunc() {
  echo "inside func"
}
myfunc 1 2 3

# TODO: Test vars don't persist.
(echo "in subshell"; echo "another")

echo \$(echo ComSub)

EOF
  $OSH _tmp/smoke-prog.sh

  echo ===== EMPTY
  touch _tmp/empty.sh 
  $OSH _tmp/empty.sh

  echo ===== NO TRAILING NEWLINE
  echo -n 'echo hi' >_tmp/no-newline.sh
  $OSH _tmp/no-newline.sh
}

# Read from stdin.
test-osh-stdin() {
  $OSH < _tmp/smoke-prog.sh

  echo ===== EMPTY
  $OSH < _tmp/empty.sh

  echo ===== NO TRAILING NEWLINE
  $OSH < _tmp/no-newline.sh

  # Line continuation tests
  $OSH <<EOF
echo "
hi
"
echo \\
line continuation; echo two

cat <<EOF_INNER
here doc
EOF_INNER

echo \$(
echo command sub
)

myfunc() {
  echo hi
}

EOF
}

test-osh-interactive() {
  set +o errexit
  echo 'echo hi' | $OSH -i
  nq-assert $? -eq 0

  echo 'exit' | $OSH -i
  nq-assert $? -eq 0

  # Parse failure
  echo ';' | $OSH -i
  nq-assert $? -eq 2

  # Bug fix: this shouldn't try execute 'echo OIL OIL'
  # The line lexer wasn't getting reset on parse failures.
  echo ';echo OIL OIL' | $OSH -i
  nq-assert $? -eq 2

  # Bug fix: c_parser.Peek() in main_loop.InteractiveLoop can raise exceptions
  echo 'v=`echo \"`' | $OSH -i
  nq-assert $? -eq 0
}

test-exit-builtin-interactive() {
  set +o errexit
  echo 'echo one; exit 42; echo two' | bin/osh -i
  nq-assert $? -eq 42
}

test-rc-file() {
  set +o errexit

  local rc=_tmp/testrc
  echo 'PS1="TESTRC$ "' > $rc

  bin/osh -i --rcfile $rc < /dev/null
  nq-assert $? -eq 0

  bin/osh -i --rcfile /dev/null < /dev/null
  nq-assert $? -eq 0

  # oshrc is optional
  # TODO: Could warn about nonexistent explicit --rcfile?
  bin/osh -i --rcfile nonexistent__ < /dev/null
  nq-assert $? -eq 0
}

test-noexec-fails-properly() {
  set +o errexit
  local tmp=_tmp/osh-usage-noexec.txt
  bin/osh -n -c 'echo; echo; |' > $tmp
  nq-assert $? -eq 2
  read < $tmp
  nq-assert $? -eq 1  # shouldn't have read any lines!
  echo "$tmp appears empty, as expected"
}

test-help() {
  local status

  # TODO: Test the oil.ovm binary as well as bin/oil.py.
  export PYTHONPATH='.:vendor/'  # TODO: Put this in one place.

  # Bundle usage.
  nq-run status \
    bin/oils_for_unix.py --help
  nq-assert $status -eq 0

  # Pass applet as first name.
  nq-run status \
    bin/oils_for_unix.py osh --help
  nq-assert $status -eq 0

  nq-run status \
    bin/oils_for_unix.py ysh --help
  nq-assert $status -eq 0

  # Symlinks.
  nq-run status \
    bin/osh --help
  nq-assert $status -eq 0

  nq-run status \
    bin/oils_for_unix.py  --help
  nq-assert $status -eq 0
}

test-version() {
  local status

  nq-run status \
    bin/osh --version
  nq-assert $? -eq 0
}

DISABLED-test-symlink() {
  local tmp=_tmp/osh-usage
  mkdir -p $tmp

  local repo_root=$PWD

  # requires 'make'
  local bundle=$PWD/_bin/oil.ovm 
  #local bundle=$repo_root/bin/oil.py

  ln -s -f -v $bundle $tmp/osh
  ln -s -f -v $bundle $tmp/bash

  cd $tmp

  ./osh -c 'echo $OILS_VERSION'
  nq-assert $? -eq 0
  ./bash -c 'echo $OILS_VERSION'
  nq-assert $? -eq 0
}

# TODO: Use byo test for these two functions

run-for-release() {
  run-other-suite-for-release osh-usage run-test-funcs
}

soil-run() {
  run-test-funcs
}

"$@"

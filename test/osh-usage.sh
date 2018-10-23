#!/usr/bin/env bash
#
# Test osh usage "from the outside".
#
# Usage:
#   ./osh-usage.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source test/common.sh

# Doesn't work in release automation!
manual-oheap-test() {
  # Not dumping to terminal
  if bin/osh -n --ast-format oheap -c 'echo hi'; then
    die "Should have failed"
  fi
  echo OK
}

ast-formats() {
  bin/osh -n -c 'echo hi'
  bin/osh -n --ast-format text -c 'echo hi'
  bin/osh -n --ast-format abbrev-html -c 'echo hi'
  bin/osh -n --ast-format html -c 'echo hi'

  local ast_bin=_tmp/smoke-ast.bin 
  bin/osh -n --ast-format oheap -c 'echo hi' > $ast_bin
  ls -l $ast_bin
  hexdump -C $ast_bin
}

# Read from a file.
osh-file() {
  echo ===== Hello
  cat >_tmp/smoke-prog.sh <<EOF
echo hi

func() {
  echo "inside func"
}
func 1 2 3

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
osh-stdin() {
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

func() {
  echo hi
}

EOF
}

osh-interactive() {
  set +o errexit
  echo 'echo hi' | $OSH -i

  echo 'exit' | $OSH -i

  # Parse failure
  echo ';' | $OSH -i

  # Bug fix: this shouldn't try execute 'echo OIL OIL'
  # The line lexer wasn't getting reset on parse failures.
  echo ';echo OIL OIL' | $OSH -i
}

help() {
  set +o errexit

  # TODO: Test the oil.ovm binary as well as bin/oil.py.
  export PYTHONPATH=.

  # Bundle usage.
  bin/oil.py --help
  assert $? -eq 0

  # Pass applet as first name.
  bin/oil.py osh --help
  assert $? -eq 0

  bin/oil.py oil --help
  assert $? -eq 0

  # Symlinks.
  bin/osh --help
  assert $? -eq 0

  bin/oil --help
  assert $? -eq 0
}

exit-builtin-interactive() {
  set +o errexit
  echo 'echo one; exit 42; echo two' | bin/osh -i
  assert $? -eq 42
}

readonly -a PASSING=(
  ast-formats
  osh-file
  osh-stdin
  osh-interactive
  exit-builtin-interactive
  help
)

all-passing() {
  run-all "${PASSING[@]}"
}

run-for-release() {
  run-other-suite-for-release osh-usage all-passing
}

"$@"

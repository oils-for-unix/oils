#!/usr/bin/env bash
#
# Sanity checks for the shell.
#
# Usage:
#   ./smoke.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source test/common.sh

ast() {
  bin/osh -n -c 'echo hi'
  bin/osh -n --ast-format text -c 'echo hi'
  bin/osh -n --ast-format abbrev-html -c 'echo hi'
  bin/osh -n --ast-format html -c 'echo hi'

  # Not dumping to terminal
  if bin/osh -n --ast-format oheap -c 'echo hi'; then
    die "Should have failed"
  fi
  local ast_bin=_tmp/smoke-ast.bin 
  bin/osh -n --ast-format oheap -c 'echo hi' > $ast_bin
  ls -l $ast_bin
  hexdump -C $ast_bin
}


# Read from a file.
osh-file() {
  echo ===== Hello
  cat >_tmp/hi.sh <<EOF

echo hi
echo bye

func() {
  echo "inside func"
}
func 1 2 3

# TODO: Test vars don't persist.
(echo "in subshell"; echo "another")

echo \$(echo ComSub)

EOF
  $OSH _tmp/hi.sh

  echo ===== EMPTY
  touch _tmp/empty.sh 
  $OSH _tmp/empty.sh

  echo ===== NO TRAILING NEWLINE
  echo -n 'echo hi' >_tmp/no-newline.sh
  $OSH _tmp/no-newline.sh
}

# Read from stdin.
osh-stdin() {
  $OSH < _tmp/hi.sh 

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
# TODO: test while loop
}

osh-interactive() {
  echo 'echo hi' | $OSH -i

  echo 'exit' | $OSH -i
}

help() {
  set +o errexit

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

_error-case() {
  echo
  echo "$@"
  echo
  bin/osh -c "$@"
}

parse-errors() {
  set +o errexit
  _error-case 'echo < <<'
  _error-case '${foo:}'
  _error-case '$(( 1 +  ))'
  _error-case 'echo $( echo > >>  )'
  #_error-case 'echo ${'
}

exit-builtin-interactive() {
  set +o errexit
  echo 'echo one; exit 42; echo two' | bin/osh -i
  assert $? -eq 42
}

readonly -a PASSING=(
  ast
  osh-file
  osh-stdin
  osh-interactive
  exit-builtin-interactive
  help
)

all-passing() {
  run-all "${PASSING[@]}"
}

"$@"

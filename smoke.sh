#!/bin/bash
#
# Sanity checks for the shell.
#
# Usage:
#   ./smoke.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

readonly OSH=bin/osh

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

"$@"

#!/usr/bin/env bash
#
# Usage:
#   demo/matchertext.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

m-extensible() {
  local lang=$1
  shift
  if "$@"; then
    echo
    echo "[$lang] NO, expected syntax error"
  else
    echo
    echo "[$lang] YES"
  fi

  echo
  echo ---
  echo
}

demo() {
  echo 'Are the C-style string literals in this language M-extensible?'
  echo 'We simply test them for syntax errors after a \'
  echo
  echo 'This is also relevant to YSTR, where we add \xff and \u{012345} escapes'
  echo

  local tmp=/tmp/foo.c

  cat >$tmp <<'EOF'
import json
json.loads('"\[]"')
json.loads('"\m[]"')
EOF
  m-extensible 'JSON' python3 $tmp

  cat >$tmp <<'EOF'
#include <stdio.h>
int main() {
  printf("\[]\n");
  printf("\m[]\n");
}
EOF
  m-extensible 'C' gcc -o /tmp/m $tmp


  echo 'Running C'

  # See what the output looks like
  chmod +x /tmp/m
  /tmp/m

  echo
  echo ---

  m-extensible 'Python' python3 -c '
print("\[]")
print("\m[]")
'

  m-extensible 'Shell' sh -c '
echo "\[]"
echo "\m[]"
'

  # awk has warnings
  echo input | m-extensible 'Awk' awk '
{
  print("\[]");
  print("\m[]");
}
'

  m-extensible 'JavaScript' nodejs -e '
console.log("\[]");
console.log("\m[]");
'

}

"$@"

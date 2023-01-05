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

# Other languages to test:
#
# - CSV -- seems unlikely that there is any syntactic room
# - YAML -- maybe in its JSON subset, however most people seem to use the
#   indented strings with a whitespace rule
# - HTML and XML - addressed as '*ML' in the paper

demo() {
  echo 'Are the string literals in this language M-extensible?'
  echo 'We simply test them for syntax errors after a special char like \'
  echo
  echo 'This is also relevant to YSTR, where we add \xff and \u{012345} escapes'
  echo

  mkdir -p _tmp

  local tmp=_tmp/foo.c

  cat >$tmp <<'EOF'
import json
json.loads('"\[]"')
json.loads('"\m[]"')
EOF
  m-extensible 'JSON' python3 $tmp


  # The only metacharacter in Ninja is $, and a literal dollar is $$ (similar
  # to GNU make)
  #
  # You could imagine a matchertext literal as $[ cp $SHELL_VAR_NOT_NINJA_VAR x ]
  #
  # Ninja and GNU make's conflict with shell annoys me

  echo foo > _tmp/ninja-in

  cat >_tmp/z.ninja <<'EOF'
rule copy
  command = cp $in $out

build _tmp/out : copy _tmp/ninja-in

build _tmp/$[ : copy _tmp/ninja-in

EOF
  m-extensible 'Ninja' ninja -f _tmp/z.ninja


  echo foo > _tmp/make-in

  cat >_tmp/z.mk <<'EOF'
_tmp/make-out : _tmp/make-in
	cp $< $@

_tmp/make-out : _tmp/make-in
	cp $[ $< $@
EOF
  m-extensible 'GNU Make' make -f _tmp/z.mk

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

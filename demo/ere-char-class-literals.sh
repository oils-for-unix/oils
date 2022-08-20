#!/usr/bin/env bash
#
# Usage:
#   ./ere-char-class-literals.sh <function name>

set -o nounset
set -o pipefail
#set -o errexit

readonly FILE=_tmp/ere-test.txt

setup() {
  { cat <<'EOF'
aaa
b-b
ccc
^ caret
\ backslash
[ left bracket
] right bracket
EOF

  # embedded NUL
  # OSH Python bindings don't like this!  gah!
  #echo -e 'NUL \x00 NUL'

  echo -e '\xff 0xff'

  } > $FILE

  od -c $FILE
}

survey-shell() {
  local ere=$1

  while read -r line; do
    if [[ $line =~ $ere ]]; then
      echo $line
    fi
  done < $FILE
}

survey() {
  local ere=$1

  echo ====
  echo "$ere"
  echo ====

  # Supports \ escapes
  echo '    GAWK'
  gawk 'match($0, /'$ere'/, m) { print $0 }' $FILE

  # Supports \ escapes
  echo '    MAWK'
  mawk '$0 ~ /'$ere'/ { print $0 }' $FILE

  echo '    EGREP'
  egrep "$ere" $FILE

  echo '    BASH'
  survey-shell "$ere"

  echo '    OSH'
  bin/osh $0 survey-shell "$ere"
}

test-ere() {

  survey '[-]'

  #survey '^'  # beginning of line
  #survey '[^]'  # invalid

  # OK this seems to work, and doesn't include \
  survey '\^'  

  # searches for backslash AND caret, except for gawk
  survey '[\^]'

  survey '[]]'
  survey '[[]'

  # are hex escapes supported?  GAWK only!
  survey '[\x2d]'

  # gawk has problems because of extension!!!  Must escape
  #survey '[\]'

  survey '[\\]'

  # single byte matching doesn't work with en_US.UTF-8 !
  echo LANG=$LANG
  survey "[$(echo -e '\xff')]"

  # it DOES work with LANG=C
  LANG=C
  echo LANG=$LANG
  declare -p LANG  # it's exported!
  survey "[$(echo -e '\xff')]"

  #survey "$(echo -e '\xff')"
}


argv() {
  spec/bin/argv.py "$@"
}

ere-capture-order() {
  # It feels like it's a depth first walk
  # It basically goes in order of the (

  pat='([a-z]+)([0-9]+)'
  [[ abc123 =~ $pat ]]; argv "${BASH_REMATCH[@]}"

  pat='(([a-z])([a-z])[a-z])([0-9]+)'
  [[ abc123 =~ $pat ]]; argv "${BASH_REMATCH[@]}"

  # Extra parens DOES create a new capture
  pat='((([a-z]))([a-z])[a-z])([0-9]+)'
  [[ abc123 =~ $pat ]]; argv "${BASH_REMATCH[@]}"

  pat='(([a-z][a-z])[a-z])([0-9]+)'
  [[ abc123 =~ $pat ]]; argv "${BASH_REMATCH[@]}"

  pat='(([a-z]([a-z]))[a-z])(([0-9]+))'
  [[ abc123 =~ $pat ]]; argv "${BASH_REMATCH[@]}"
}

"$@"


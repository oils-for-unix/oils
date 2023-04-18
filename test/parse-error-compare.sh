#!/usr/bin/env bash
#
# Usage:
#   test/parse-error-compare.sh <function name>
#
# Example:
#   test/parse-error-compare.sh all

set -o nounset
set -o pipefail

log() {
  echo "$@" >& 2
}

show-case() {
  local desc=$1
  local code=$2

  echo '-------------------------'
  echo "$desc"
  echo "$code"
  echo

  local status

  for sh in bash dash zsh mksh bin/osh; do
    $sh -n -c "$code"
    status=$?

    #echo status=$status

    if test $status -eq 0; then
      log "Expected non-zero status"
      exit 1
    fi

    echo
  done
}

test-for-loop() {
  ### test for loop errors

  show-case 'for missing semi-colon' '
for i in 1 2 do
  echo $i
done
'

  show-case 'for missing do' '
for i in 1 2
  echo $i
done
'

  show-case 'for semi in wrong place' '
for i in 1 2 do;
  echo $i
done
'

  show-case 'trying to use JS style' '
for (i in x) {
  echo $i
}
'
}

test-while-loop() {
  ### Same thing for while loops

  show-case 'while missing semi' '
while test -f file do
  echo $i
done
'

  show-case 'while missing do' '
while test -f file 
  echo $i
done
'

  show-case 'while semi in wrong place' '
while test -f file do;
  echo $i
done
'
}

test-if() {
  ### Same thing for if statements

  show-case 'if missnig semi' '
if test -f file then
  echo $i
fi
'

  show-case 'if missing then' '
if test -f file 
  echo $i
fi
'

  show-case 'if semi in wrong place' '
if test -f file then;
  echo $i
fi
'
}

test-case() {
  show-case 'missing ;;' '
case $x in
  x) echo missing
  y) echo missing
esac
'
}

all() {
  compgen -A function | egrep '^test-' | while read func; do
    echo ====
    echo "$func"
    echo ====
    echo

    $func
    echo
    echo

  done
}

"$@"

#!/usr/bin/env bash
#
# Usage:
#   test/parse-error-compare.sh <function name>
#
# Example:
#   test/parse-error-compare.sh all

set -o nounset
set -o pipefail

show-case() {
  local desc=$1
  local code=$2

  echo '-------------------------'
  echo $desc
  echo "$code"
  echo

  for sh in bash dash bin/osh; do
    $sh -n -c "$code"
    echo
  done
}

all() {
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

  ### Same thing for while loops statements

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

"$@"

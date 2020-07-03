#!/bin/bash
#
# Usage:
#   ./regex-backtrack.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

# https://swtch.com/~rsc/regexp/regexp1.html

repeat() {
  local s=$1
  local n=$2

  for i in $(seq $n); do
    echo -n "$s"
  done
}

pattern() {
  local n=$1

  # a?^n a^n
  repeat 'a?' $n
  repeat 'a' $n
  echo
}

text() {
  local n=$1
  repeat a $n
  echo
}

demo() {
  pattern 1
  pattern 2
  pattern 3

  text 1
  text 2
  text 3
}

egrep-task() {
  local text=$1
  local pattern=$2

  echo -n 'eg '
  echo "$text" | egrep "$pattern" || true
}

python-task() {
  local text=$1
  local pattern=$2

  echo -n 'py '
  python -c '
import re, sys

pattern, text = sys.argv[1:]
#print(pattern)
#print(text)
print(re.match(pattern, text).group(0))
' "$pattern" "$text"
}

benchmark() {
  local max=${1:-20}

  TIMEFORMAT='%U'  # CPU seconds spent in user mode

  for i in $(seq $max); do
    local pattern=$(pattern $i)
    local text=$(text $i)

    time egrep-task "$text" "$pattern"
    time python-task "$text" "$pattern"
    echo
  done
}

"$@"

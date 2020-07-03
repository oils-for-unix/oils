#!/bin/bash
#
# Demo for EggEx.  Do any of these common engines backtrack?
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

  echo -n 'egrep '
  echo "$text" | egrep "$pattern"
}

sed-task() {
  local text=$1
  local pattern=$2

  echo -n 'sed   '
  echo "$text" | sed "/$pattern/p"
}

awk-task() {
  local bin=$1
  local text=$2
  local pattern=$3

  echo -n "$bin  "
  echo "$text" | $bin "/$pattern/ { print }"
}

mawk-task() { awk-task mawk "$@"; }
gawk-task() { awk-task gawk "$@"; }

libc-task() {
  ### bash is linked against libc

  local text=$1
  local pattern=$2

  echo -n 'libc  '
  # note: pattern can't be quoted
  [[ "$text" =~ $pattern ]] && echo $text
}

python-task() {
  local text=$1
  local pattern=$2

  echo -n 'py    '
  python -c '
import re, sys

pattern, text = sys.argv[1:]
#print(pattern)
#print(text)

# Assumed to match
print(re.match(pattern, text).group(0))
' "$pattern" "$text"
}

perl-task() {
  local text=$1
  local pattern=$2

  echo -n 'perl  '
  echo "$text" | perl -n -e "print if /$pattern/"

  # https://stackoverflow.com/questions/4794145/perl-one-liner-like-grep
}

benchmark() {
  local max=${1:-22}

  TIMEFORMAT='%U'  # CPU seconds spent in user mode

  for i in $(seq $max); do
    local pattern=$(pattern $i)
    local text=$(text $i)

    time egrep-task "$text" "$pattern"
    time sed-task "$text" "$pattern"
    time libc-task "$text" "$pattern"
    time gawk-task "$text" "$pattern"
    time mawk-task "$text" "$pattern"
    time python-task "$text" "$pattern"
    time perl-task "$text" "$pattern"
    echo
  done
}

"$@"

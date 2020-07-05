#!/bin/bash
#
# Demo for EggEx.  Do any of these common engines backtrack?
#
# Related: https://research.swtch.com/glob
#
# "Perhaps the most interesting fact evident in the graph is that GNU glibc,
# the C library used on Linux systems, has a linear-time glob implementation,
# but BSD libc, the C library used on BSD and macOS systems, has an
# exponential-time implementation."
#
# Usage:
#   ./regex-backtrack.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source demo/backtrack-lib.sh

TIMEFORMAT='%U'  # CPU seconds spent in user mode

# https://swtch.com/~rsc/regexp/regexp1.html

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
if re.match(pattern, text):
  print(text)
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

#
# glob
#

glob-setup() {
  mkdir -p $GLOB_TMP
  cd $GLOB_TMP
  touch $(repeat a 100)
  ls -l 
}

readonly -a SHELLS=(dash bash mksh _deps/spec-bin/ash bin/osh)

glob-compare() {
  # bash and mksh both backtrack
  # dash and ash are OK.  osh is good too!  with GNU libc.

  # - zsh doesn't source it?
  # - yash doesn't like 'local'.

  for sh in ${SHELLS[@]}; do
    echo === $sh
    $sh -c '. demo/backtrack-lib.sh; glob_bench'
  done

}

fnmatch-compare() {
  # Same for fnmatch(): bash and mksh backtrack
  # osh doesn't
  # but dash and ash somehow don't like 'time shellfunc'?

  for sh in ${SHELLS[@]}; do
    echo === $sh
    $sh -c '. demo/backtrack-lib.sh; fnmatch_bench'
  done
}

#
# Greedy vs. non-greedy
#
# sed, python, perl, gawk have captures
#

egrep-match() {
  local text=$1
  local pat=$2

  echo -n 'egrep '
  # -o for only matching portion
  echo "$text" | egrep -o "$pat"
}

sed-match() {
  local text=$1
  local pat=$2

  echo -n 'sed   '
  #echo "$text" | sed -r -n 's/'"$pat"'/&/p'

  # you need these extra .* in sed.  Because of the way the 's' command works.
  # But that breaks some stuff

  # https://stackoverflow.com/questions/2777579/how-to-output-only-captured-groups-with-sed/43997253

  echo "$text" | sed -r -n 's/.*('"$pat"').*/\1/p'

  #echo "$text" | sed "/$pat/p"
}

libc-match() {
  local text=$1
  local pat=$2

  echo -n 'libc  '
  [[ "$text" =~ $pat ]]
  echo ${BASH_REMATCH[0]}
}

gawk-match() {
  local text=$1
  local pat=$2

  echo -n 'gawk  '
  echo "$text" | gawk 'match($0, /'"$pat"'/, m) { print m[0] }'
}

python-match() {
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

perl-match() {
  local text=$1
  local pat=$2

  # I can't figure out how to do the equivalent of $0 in Perl?
  echo -n 'perl  '
  echo "$text" | perl -n -e '$_ = /('"$pat"')/; print $1'
  echo
}

greedy() {
  local text='<p>hello</p> foo'

  for pat in '<.*>' '<.*>h'; do
    echo
    echo "=== matching against $pat"
    echo

    time egrep-match "$text" "$pat"

    #local pat2='\<.*\>h'
    time sed-match "$text" "$pat"

    time libc-match "$text" "$pat"
    time gawk-match "$text" "$pat"
    time python-match "$text" "$pat"
    time perl-match "$text" "$pat"
  done

  echo
  echo '== nongreedy'
  echo

  # Only backtracking engines support this non-greedy behavior
  pat='<.*?>'
  time python-match "$text" "$pat"
  time perl-match "$text" "$pat"
}

#
# Capture Semantics -- the "parse problem"
#

libc-submatch() {
  local text=$1
  local pat=$2

  echo -n 'libc  '
  [[ "$text" =~ $pat ]]
  echo ${BASH_REMATCH[1]}
}

gawk-submatch() {
  local text=$1
  local pat=$2

  echo -n 'gawk  '
  echo "$text" | gawk 'match($0, /'"$pat"'/, m) { print m[1] }'
}

sed-submatch() {
  local text=$1
  local pat=$2

  echo -n 'sed   '
  echo "$text" | sed -r -n 's/'"$pat"'/\1/p'
}

python-submatch() {
  local text=$1
  local pattern=$2

  echo -n 'py    '
  python -c '
import re, sys

pattern, text = sys.argv[1:]
#print(pattern)
#print(text)

# Assumed to match
print(re.match(pattern, text).group(1))
' "$pattern" "$text"
}

perl-submatch() {
  local text=$1
  local pat=$2

  echo -n 'perl  '
  echo "$text" | perl -n -e '$_ = /'"$pat"'/; print $1'
  echo
}

# Digression: POSIX submatching
# https://swtch.com/~rsc/regexp/regexp2.html

submatch() {
  local text='abcdefg'
  local pat='(a|bcdef|g|ab|c|d|e|efg|fg)*'

  # Simpler version
  local text='abc'
  local pat='(a|bc|ab|c)*'

  # they all print 'g' ?
  # So there's no difference?

  # These are POSIX conformance bugs?
  # 2010: http://hackage.haskell.org/package/regex-posix-unittest
  # https://wiki.haskell.org/Regex_Posix

  libc-submatch "$text" "$pat"
  gawk-submatch "$text" "$pat"
  sed-submatch "$text" "$pat"

  python-submatch "$text" "$pat"
  perl-submatch "$text" "$pat"
}

"$@"

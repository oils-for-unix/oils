#!/usr/bin/env bash
#
# Measure the number of syscalls that shells use.
#
# Usage:
#   test/syscall.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source build/dev-shell.sh

readonly -a SHELLS=(dash bash mksh zsh ash yash osh)

readonly BASE_DIR='_tmp/syscall'  # What we'll publish
readonly RAW_DIR='_tmp/syscall-raw'  # Raw data

# Run it against the dev version of OSH
REPO_ROOT=$(cd $(dirname $(dirname $0)) && pwd)

count-procs() {
  local out_prefix=$1
  local sh=$2
  shift 2

  case $sh in 
    # avoid the extra processes that bin/osh starts!
    # relies on word splitting
    #(X)  # to compare against osh 0.8.pre3 installed
    (osh)
      sh="env PYTHONPATH=$REPO_ROOT:$REPO_ROOT/vendor $REPO_ROOT/bin/oil.py osh"
      ;;
  esac

  strace -ff -o $out_prefix -- $sh "$@"
}

run-case() {
  ### Run a test case with many shells

  local num=$1
  local code_str=$2

  for sh in "${SHELLS[@]}"; do
    local out_prefix=$RAW_DIR/$num-$sh
    echo "--- $sh"
    count-procs $out_prefix $sh -c "$code_str"
  done
}

run-case-file() {
  ### Like the above, but the shell reads from a file

  local num=$1
  local code_str=$2

  echo -n "$code_str" > _tmp/$num.sh

  for sh in "${SHELLS[@]}"; do
    local out_prefix=$RAW_DIR/$num-$sh
    echo "--- $sh"
    count-procs $out_prefix $sh _tmp/$num.sh
  done
}

run-case-stdin() {
  ### Like the above, but read from a pipe

  local num=$1
  local code_str=$2

  for sh in "${SHELLS[@]}"; do
    local out_prefix=$RAW_DIR/$num-$sh
    echo "--- $sh"
    echo -n "$code_str" | count-procs $out_prefix $sh
  done
}


print-cases() {
  # format:  number, whitespace, then an arbitrary code string
  egrep -v '^[[:space:]]*(#|$)' <<EOF

# builtin
echo hi

# external command
date

# Oil sentence
date ;

# external then builtin
date; echo hi

# builtin then external
echo hi; date

# two external commands
date; date

# does a brace group make a difference?
{ date; date; }

# singleton brace group
date; { date; }

# does it behave differently if sourced?
. _tmp/sourced.sh

# dash and zsh somehow optimize this to 1
(echo hi)

(date)

( ( date ) )

( ( date ) ); echo hi

echo hi; (date)

# Sentence in Oil
(date;) > /tmp/out.txt

(date; echo hi)

# command sub
echo \$(date)

# command sub with builtin
echo \$(echo hi)

# command sub with useless subshell (some scripts use this)
echo \$( ( date ) )

# command sub with other subshell
echo \$( ( date ); echo hi )

# 2 processes for all shells
( echo hi ); echo done

# simple pipeline
date | wc -l

# every shell does 3
echo a | wc -l

# every shell does 3
command echo a | wc -l

# bash does 4 here!
command date | wc -l

# 3 processes for all?
# osh gives FIVE???  But others give 3.  That's bad.
( date ) | wc -l

# 3 processes for all shells except zsh and osh, which have shopt -s lastpipe!
date | read x

# osh has 3, but should be 2 like zsh?
# hm how can zsh do 2 here?  That seems impossible.
# oh it's lastpipe turns the shell process into wc -l ???  wow.
{ echo a; echo b; } | wc -l

# zsh behaves normally here.  That is a crazy optimization.  I guess it's
# nice when you have SH -c 'mypipeline | wc-l'
{ echo a; echo b; } | wc -l; echo done

# this is all over the map too.  3 4 4 2.
{ echo a; date; } | wc -l

# osh does 4 when others do 3.  So every shell optimizes this extra pipeline.
( echo a; echo b ) | wc -l

# osh does 5 when others do 3.
( echo a; echo b ) | ( wc -l )
EOF

# Discarded because they're identical
# pipeline with redirect last
#date | wc -l > /tmp/out.txt

# pipeline with redirect first
#date 2>&1 | wc -l

}

number-cases() {
  # Right justified, leading zeros, with 2
  # Wish this was %02d
  print-cases | nl --number-format rz --number-width 2
}

by-input() {
  ### Run cases that vary by input reader

  local suite='by-input'

  shopt -s nullglob
  rm -f -v $RAW_DIR/*

  # Wow this newline makes a difference in shells!

  # This means that Id.Eof_Real is different than Id.Op_Newline?
  # Should we create a Sentence for it too then?
  # That is possible in _ParseCommandLine

  zero=$'date; date'
  one=$'date; date\n'
  two=$'date; date\n#comment\n'
  comment=$'# comment\ndate;date'
  newline=$'date\n\ndate'
  newline2=$'date\n\ndate\n#comment'

  # zsh is the only shell to optimize all 6 cases!  2 processes instead of 3.
  run-case 30 "$zero"
  run-case 31 "$one"
  run-case 32 "$two"
  run-case 33 "$comment"
  run-case 34 "$newline"
  run-case 35 "$newline2"

  run-case-file 40 "$zero"
  run-case-file 41 "$one"
  run-case-file 42 "$two"
  run-case-file 43 "$comment"
  run-case-file 44 "$newline2"
  run-case-file 45 "$newline2"

  # yash is the only shell to optimize the stdin case at all!
  # it looks for a lack of trailing newline.
  run-case-stdin 50 "$zero"
  run-case-stdin 51 "$one"
  run-case-stdin 52 "$two"
  run-case-stdin 53 "$comment"
  run-case-stdin 54 "$newline2"
  run-case-stdin 55 "$newline2"

  # This is identical for all shells
  #run-case 32 $'date; date\n#comment\n'

  cat >$BASE_DIR/${suite}-cases.txt <<EOF
30 -c: zero lines
31 -c: one line
32 -c: one line and comment
33 -c: comment first
34 -c: newline
35 -c: newline2
40 file: zero lines
41 file: one line
42 file: one line and comment
43 file: comment first
44 file: newline
45 file: newline2
50 stdin: zero lines
51 stdin: one line
52 stdin: one line and comment
53 stdin: comment first
54 stdin: newline
55 stdin: newline2
EOF

  count-lines $suite
  summarize $suite 3 0

}

# Quick hack: every shell uses 2 processes for this... doesn't illuminate much.
weird-command-sub() {
  shopt -s nullglob
  rm -f -v $RAW_DIR/*

  local tmp=_tmp/cs
  echo FOO > $tmp
  run-case 60 "echo $(< $tmp)"
  run-case 61 "echo $(< $tmp; echo hi)"

  local suite=weird-command-sub

  cat >$BASE_DIR/${suite}-cases.txt <<EOF
60 \$(< file)
61 \$(< file; echo hi)
EOF

  count-lines $suite
  summarize $suite 0 0
}

readonly MAX_CASES=100
#readonly MAX_CASES=3

by-code() {
  ### Run cases that vary by code snippet

  local max_cases=${1:-$MAX_CASES}

  mkdir -p $RAW_DIR $BASE_DIR

  write-sourced

  shopt -s nullglob
  rm -f -v $RAW_DIR/*

  local suite='by-code'
  local cases=$BASE_DIR/${suite}-cases.txt

  number-cases > $cases
  head -n $max_cases $cases | while read -r num code_str; do
    echo
    echo '==='
    echo "$num     $code_str"
    echo

    run-case $num "$code_str"
  done

  # omit total line
  count-lines $suite
  summarize $suite 3 0
}

syscall-py() {
  PYTHONPATH=. test/syscall.py "$@"
}

write-sourced() {
  echo -n 'date; date' > _tmp/sourced.sh
}

count-lines() {
  local suite=${1:-by-code}
  ( cd $RAW_DIR && wc -l * ) | head -n -1 > $BASE_DIR/${suite}-counts.txt
}

summarize() {
  local suite=${1:-by-code}
  local not_minimum=${2:-0}
  local more_than_bash=${3:-0}

  local out=$BASE_DIR/${suite}.txt
  set +o errexit
  cat $BASE_DIR/${suite}-counts.txt \
    | syscall-py --not-minimum $not_minimum --more-than-bash $more_than_bash \
                 $BASE_DIR/${suite}-cases.txt \
    > $out
  local status=$?
  set -o errexit

  echo "Wrote $out"
  if test $status -eq 0; then
    echo 'OK'
  else
    echo 'FAIL'
  fi
}

run-for-release() {
  ### Run the two syscall suites

  # Invoked as one of the "other" tests.  Note: This is different than what
  # 'toil' runs.  Might want to unify them.

  by-code
  by-input

  local dest=_tmp/other/syscall/
  mkdir -p $dest

  cp -v ${BASE_DIR}/by-code.txt ${BASE_DIR}/by-input.txt $dest

  echo 'OK'
}


"$@"

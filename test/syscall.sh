#!/usr/bin/env bash
#
# Measure the number of syscalls that shells use.
#
# Usage:
#   test/syscall.sh <function name>

: ${LIB_OSH=stdlib/osh}
source $LIB_OSH/bash-strict.sh
source $LIB_OSH/task-five.sh

source build/dev-shell.sh

OSH=${OSH:-osh}
YSH=${YSH:-ysh}

#readonly -a SHELLS=(dash bash-4.4 bash $OSH)

# Compare bash 4 vs. bash 5
SHELLS=(dash bash-4.4 bash-5.2.21 mksh zsh ash $OSH $YSH)

SHELLS_MORE=( ${SHELLS[@]} yash )

# yash does something fundamentally different in by-code.wrapped - it
# understands functions
#SHELLS+=(yash)

readonly BASE_DIR='_tmp/syscall'  # What we'll publish
readonly RAW_DIR='_tmp/syscall-raw'  # Raw data

# Run it against the dev version of OSH
REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)

count-procs() {
  local out_prefix=$1
  local sh=$2
  shift 2

  case $sh in 
    # avoid the extra processes that bin/osh starts!
    # relies on word splitting
    #(X)  # to compare against osh 0.8.pre3 installed
    osh)
      sh="env PYTHONPATH=$REPO_ROOT:$REPO_ROOT/vendor $REPO_ROOT/bin/oils_for_unix.py osh"
      ;;
    ysh)
      sh="env PYTHONPATH=$REPO_ROOT:$REPO_ROOT/vendor $REPO_ROOT/bin/oils_for_unix.py ysh"
      ;;
    osh-cpp)
      sh=_bin/cxx-dbg/osh
      ;;
    ysh-cpp)
      sh=_bin/cxx-dbg/ysh
      ;;
  esac

  # Ignore failure, because we are just counting
  strace -ff -o $out_prefix -- $sh "$@" || true
}

run-case() {
  ### Run a test case with many shells

  local num=$1
  local code_str=$2
  local func_wrap=${3:-}

  local -a shells
  if test -n "$func_wrap"; then
    code_str="wrapper() { $code_str; }; wrapper"
    shells=( "${SHELLS[@]}" )
  else
    shells=( "${SHELLS_MORE[@]}" )
  fi

  for sh in "${shells[@]}"; do
    local out_prefix=$RAW_DIR/${sh}__${num}
    echo "--- $sh"
    count-procs $out_prefix $sh -c "$code_str"
  done
}

run-case-file() {
  ### Like the above, but the shell reads from a file

  local num=$1
  local code_str=$2

  echo -n "$code_str" > _tmp/$num.sh

  for sh in "${SHELLS_MORE[@]}"; do
    local out_prefix=$RAW_DIR/${sh}__${num}
    echo "--- $sh"
    count-procs $out_prefix $sh _tmp/$num.sh
  done
}

run-case-stdin() {
  ### Like the above, but read from a pipe

  local num=$1
  local code_str=$2

  for sh in "${SHELLS_MORE[@]}"; do
    local out_prefix=$RAW_DIR/${sh}__${num}
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

# OSH calls this "sentence"
date ;

# trap - bash has special logic for this
trap 'echo mytrap' EXIT; date

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

echo hi; (date;)

echo hi; (echo hi;)

echo hi; (echo hi; date)

( echo hi ); echo hi

date > /tmp/redir.txt

(date;) > /tmp/sentence.txt

date 2> /tmp/stderr.txt | wc -l

echo hi > /tmp/redir.txt

(echo hi;) > /tmp/sentence.txt

echo hi 2> /tmp/stderr.txt | wc -l

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

# negated
! date | wc -l

# every shell does 3
echo a | wc -l

# every shell does 3
command echo a | wc -l

# bash does 4 here!
command date | wc -l

# negated
! command date | wc -l

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

( echo a; echo b ) | ( wc -l )

{ echo prefix; ( echo a; echo b ); } | ( wc -l )

echo hi & wait

date & wait

echo hi | wc -l & wait

date | wc -l & wait

trap 'echo mytrap' EXIT; date & wait

trap 'echo mytrap' EXIT; date | wc -l & wait

# trap in SubProgramThunk
{ trap 'echo mytrap' EXIT; date; } & wait
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
  if ! strace true; then
    echo "Aborting because we couldn't run strace"
    return
  fi

  local suite='by-input'

  rm -r -f -v $RAW_DIR
  mkdir -p $RAW_DIR $BASE_DIR

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
  run-case 50 "$zero"
  run-case 51 "$one"
  run-case 52 "$two"
  run-case 53 "$comment"
  run-case 54 "$newline"
  run-case 55 "$newline2"

  run-case-file 60 "$zero"
  run-case-file 61 "$one"
  run-case-file 62 "$two"
  run-case-file 63 "$comment"
  run-case-file 64 "$newline2"
  run-case-file 65 "$newline2"

  # yash is the only shell to optimize the stdin case at all!
  # it looks for a lack of trailing newline.
  run-case-stdin 70 "$zero"
  run-case-stdin 71 "$one"
  run-case-stdin 72 "$two"
  run-case-stdin 73 "$comment"
  run-case-stdin 74 "$newline2"
  run-case-stdin 75 "$newline2"

  # This is identical for all shells
  #run-case 32 $'date; date\n#comment\n'

  cat >$BASE_DIR/cases.${suite}.txt <<EOF
50 -c: zero lines
51 -c: one line
52 -c: one line and comment
53 -c: comment first
54 -c: newline
55 -c: newline2
60 file: zero lines
61 file: one line
62 file: one line and comment
63 file: comment first
64 file: newline
65 file: newline2
70 stdin: zero lines
71 stdin: one line
72 stdin: one line and comment
73 stdin: comment first
74 stdin: newline
75 stdin: newline2
EOF

  count-lines $suite
  summarize $suite 3 0
}

# Quick hack: every shell uses 2 processes for this... doesn't illuminate much.
weird-command-sub() {
  shopt -s nullglob
  rm -r -f -v $RAW_DIR/*

  local tmp=_tmp/cs
  echo FOO > $tmp
  run-case 60 "echo $(< $tmp)"
  run-case 61 "echo $(< $tmp; echo hi)"

  local suite=weird-command-sub

  cat >$BASE_DIR/cases.${suite}.txt <<EOF
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
  local func_wrap=${1:-}

  if ! strace true; then
    echo "Aborting because we couldn't run strace"
    return
  fi

  local max_cases=${1:-$MAX_CASES}

  rm -r -f -v $RAW_DIR
  mkdir -p $RAW_DIR $BASE_DIR

  write-sourced

  local suite
  if test -n "$func_wrap"; then
    suite='by-code-wrapped'
  else
    suite='by-code'
  fi

  local cases=$BASE_DIR/cases.${suite}.txt

  number-cases > $cases
  head -n $max_cases $cases | while read -r num code_str; do
    echo
    echo '==='
    echo "$num     $code_str"
    echo

    run-case $num "$code_str" "$func_wrap"
  done

  # omit total line
  count-lines $suite
  summarize $suite 3 0
}

by-code-cpp() {
  ninja _bin/cxx-dbg/{osh,ysh}
  OSH=osh-cpp YSH=ysh-cpp $0 by-code "$@"
}

by-input-cpp() {
  ninja _bin/cxx-dbg/{osh,ysh}
  OSH=osh-cpp YSH=ysh-cpp $0 by-input "$@"
}

syscall-py() {
  PYTHONPATH=. test/syscall.py "$@"
}

write-sourced() {
  echo -n 'date; date' > _tmp/sourced.sh
}

count-lines() {
  local suite=${1:-by-code}
  ( cd $RAW_DIR && wc -l * ) | head -n -1 > $BASE_DIR/wc.${suite}.txt
}

summarize() {
  local suite=${1:-by-code}
  local not_minimum=${2:-0}
  local more_than_bash=${3:-0}

  set +o errexit
  cat $BASE_DIR/wc.${suite}.txt \
    | syscall-py \
      --not-minimum $not_minimum \
      --more-than-bash $more_than_bash \
      --suite $suite \
      $BASE_DIR/cases.${suite}.txt \
      $BASE_DIR
  local status=$?
  set -o errexit

  if test $status -eq 0; then
    echo 'OK'
  else
    echo 'FAIL'
  fi
}

soil-run() {
  # Invoked as one of the "other" tests.  Soil runs by-code and by-input
  # separately.

  # Note: Only $BASE_DIR/*.txt is included in the release/$VERSION/other.wwz
  by-code

  # wrapped
  by-code T

  by-input

  echo 'OK'
}

run-for-release() {
  ### Run the two syscall suites

  soil-run
}

#
# Real World
#
# $ ls|grep dash|wc -l
# 6098
# $ ls|grep bash|wc -l
# 6102
# $ ls|grep osh|wc -l
# 6098
#
# So Oil is already at dash level for CPython's configure, and bash isn't
# far off.  So autoconf-generated scripts probably already use constructs
# that are already "optimal" in most shells.

readonly PY27_DIR=$PWD/Python-2.7.13

cpython-configure() {
  local raw_dir=$PWD/$RAW_DIR/real
  mkdir -p $raw_dir

  pushd $PY27_DIR
  #for sh in "${SHELLS[@]}"; do
  for sh in bash dash osh; do
    local out_prefix=$raw_dir/cpython-$sh
    echo "--- $sh"

    # TODO: Use a different dir
    count-procs $out_prefix $sh -c './configure'
  done
  popd
}

task-five "$@"

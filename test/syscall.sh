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
  local code=$3

  case $sh in 
    # avoid the extra processes that bin/osh starts!
    osh)
      sh="env PYTHONPATH=$REPO_ROOT:$REPO_ROOT/vendor $REPO_ROOT/bin/oil.py osh"
      ;;
  esac

  strace -ff -o $out_prefix -- $sh -c "$code"
}

run-case() {
  ### Run a test case with many shells

  local num=$1
  local code_str=$2

  for sh in "${SHELLS[@]}"; do
    local out_prefix=$RAW_DIR/$num-$sh
    echo "--- $sh"
    count-procs $out_prefix $sh "$code_str"
  done
}

print-cases() {
  # format:  number, whitespace, then an arbitrary code string
  egrep -v '^[[:space:]]*(#|$)' <<EOF

# builtin
echo hi

# external command
date

# external then builtin
date; echo hi

# builtin then external
echo hi; date

# two external commands
date; date

# dash and zsh somehow optimize this to 1
(echo hi)

(date)

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

readonly MAX_CASES=100
#readonly MAX_CASES=5

run-cases() {
  mkdir -p $RAW_DIR $BASE_DIR

  shopt -s nullglob
  rm -f -v $RAW_DIR/* $BASE_DIR/* 

  number-cases > $BASE_DIR/cases.txt
  cat $BASE_DIR/cases.txt | head -n $MAX_CASES | while read -r num code_str; do
    echo
    echo '==='
    echo "$num     $code_str"
    echo

    run-case $num "$code_str"
  done

  # omit total line
  ( cd $RAW_DIR && wc -l * ) | head -n -1 > $BASE_DIR/counts.txt
  summarize
}

syscall-py() {
  PYTHONPATH=. test/syscall.py "$@"
}

summarize() {
  local out=$BASE_DIR/table.txt
  set +o errexit
  cat $BASE_DIR/counts.txt \
    | syscall-py --not-minimum 15 --more-than-bash 2 $BASE_DIR/cases.txt \
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

# TODO: 
# - assert failures
# - publish to 'toil'
# - add 'run-for-release' function


"$@"

#!/bin/bash
#
# Usage:
#   ./count-procs.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

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

readonly -a SHELLS=(dash bash mksh zsh osh)
readonly BASE_DIR='_tmp/count-procs'

run-case() {
  ### Run a test case with many shells

  local num=$1
  local code_str=$2

  echo
  echo "==="
  echo "$code_str"
  echo "==="

  local base_dir=$BASE_DIR

  for sh in "${SHELLS[@]}"; do
    local out_prefix=$base_dir/$num-$sh
    echo "--- $sh ---"
    count-procs $out_prefix $sh "$code_str"
  done

  return
  echo "Process counts"

  for sh in "${SHELLS[@]}"; do
    echo "--- $sh ---"
    ls $base_dir/$sh | wc -l
  done
}

print-cases() {
  # format:  number, whitespace, then an arbitrary code string
  egrep -v '^[[:space:]]*(#|$)' <<EOF

# 1 process of course
echo hi

# dash and zsh somehow optimize this to 1
(echo hi)

# command sub
echo \$(ls)

# command sub with builtin
echo \$(echo hi)

# 2 processes for all shells
( echo hi ); echo done

# 3 processes
ls | wc -l

# every shell does 3
echo a | wc -l

# every shell does 3
command echo a | wc -l

# bash does 4 here!
command ls / | wc -l

# 3 processes for all?
# osh gives FIVE???  But others give 3.  That's bad.
( ls ) | wc -l

# 3 processes for all shells except zsh and osh, which have shopt -s lastpipe!
ls | read x

# osh has 3, but should be 2 like zsh?
# hm how can zsh do 2 here?  That seems impossible.
# oh it's lastpipe turns the shell process into wc -l ???  wow.
{ echo a; echo b; } | wc -l

# zsh behaves normally here.  That is a crazy optimization.  I guess it's
# nice when you have SH -c 'mypipeline | wc-l'
{ echo a; echo b; } | wc -l; echo done

# this is all over the map too.  3 4 4 2.
{ echo a; ls /; } | wc -l

# osh does 4 when others do 3.  So every shell optimizes this extra pipeline.
( echo a; echo b ) | wc -l

# osh does 5 when others do 3.
( echo a; echo b ) | ( wc -l )
EOF
}

number-cases() {
  # Right justified, leading zeros, with 2
  # Wish this was %02d
  print-cases | nl --number-format rz --number-width 2
}

readonly MAX_CASES=100

run-cases() {
  mkdir -p $BASE_DIR

  shopt -s nullglob
  rm -f -v $BASE_DIR/*

  number-cases > $BASE_DIR/cases.txt
  cat $BASE_DIR/cases.txt | head -n $MAX_CASES | while read -r num code_str; do
    echo $num
    echo "[$code_str]"

    run-case $num "$code_str"
  done

  ls -1 $BASE_DIR | tee $BASE_DIR/listing.txt
  summarize
}

print-table() {
  PYTHONPATH=. test/count_procs.py "$@"
}

summarize() {
  cat $BASE_DIR/listing.txt \
    | egrep -o '^[0-9]+-[a-z]+' \
    | sed 's/-/ /g' \
    | print-table $BASE_DIR/cases.txt | tee $BASE_DIR/table.txt
}


"$@"

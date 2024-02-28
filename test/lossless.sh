#!/usr/bin/env bash
#
# Test the lossless invariant, which is useful for --tool ysh-ify and --tool
# fmt.
#
# Usage:
#   test/arena.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source test/common.sh  # for run-other-suite-for-release
source test/wild-runner.sh  # For MANIFEST, etc.

_compare() {
  local path=$1
  local sh=${2:-bin/osh}

  mkdir -p _tmp/arena
  $sh --tool arena $path > _tmp/arena/left.txt
  if diff -u $path _tmp/arena/left.txt; then
	  echo "$path"
  else
	  return 1
  fi
}

test-here-doc() {
  _compare test/arena/here-dq.sh
  _compare test/arena/here-sq.sh

  # Hard test case!
  _compare test/arena/here-multiple.sh

  # This is a known exception to the arena invariant.  The leading tabs aren't
  # preserved, because we don't need them for ysh-ify translation.
  _compare test/arena/here-dq-indented.sh
}

test-tilde() {
  _compare test/arena/tilde.sh
}

test-ysh() {
  for file in ysh/testdata/*.ysh; do
    echo "--- $file"
    _compare $file bin/ysh
  done
}

_compare-wild() {
  local rel_path=$1
  local abs_path=$2

  _compare $abs_path
}

# Run on wild corpus.  I think this never passed?
DISABLED-test-wild() {
  wc -l $MANIFEST
  cat $MANIFEST | xargs -n 2 -- $0 _compare-wild
}

test-big() {
  local num_files=0
  local num_passed=0

  local osh=bin/osh

  if false; then
    local osh_cpp=_bin/cxx-asan/osh
    ninja $osh_cpp
    osh=$osh_cpp
  fi

  for file in benchmarks/testdata/*; do
    echo "--- $file"
    echo
    set +o errexit
    time _compare $file $osh
    local status=$?
    set -o errexit

    if test $status = 0; then
      num_passed=$((num_passed+1))
    fi
    num_files=$((num_files+1))
  done

  # How do we handle this in tools/ysh_ify.py ?

  # 8 of 10 passed!
  echo
  echo "$num_passed of $num_files files respect the arena invariant"
  echo 'TODO: here docs broken!'
}

test-do-lossless-flag() {

  local sh_array='a[x+1]=1'

  # This gives you arithmetic parsing
  bin/osh -n -c "$sh_array"
  # This gives you a sh_lhs.UnparsedIndex token!
  bin/osh --do-lossless -n -c "$sh_array"

  local backticks='`echo \`hostname\` zzz`'

  # This gives you NESTED Id.Left_Backtick and Id.Backtick_Right
  bin/osh -n -c "$backticks"

  # This gives (an erroneous?) Lit_EscapedChar
  bin/osh --do-lossless -n -c "$backticks"

	local here=_tmp/lossless-here.sh 
  cat >$here <<EOF
cat <<-'HERE'
	one     # tabs stripped
		two   # 2 tabs
	three
	HERE
EOF

  # TODO: There will be a difference here
  bin/osh -n $here
  bin/osh --do-lossless -n $here
}

run-for-release() {
  run-other-suite-for-release arena run-test-funcs
}

soil-run() {
  run-test-funcs
}

"$@"

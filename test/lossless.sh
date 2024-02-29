#!/usr/bin/env bash
#
# Test the lossless invariant, which is useful for --tool ysh-ify and --tool
# fmt.
#
# Usage:
#   test/lossless.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source test/common.sh  # for run-other-suite-for-release
source test/wild-runner.sh  # For MANIFEST, etc.

OSH=${OSH:-bin/osh}
YSH=${YSH:-bin/ysh}

_compare() {
  local path=$1
  local sh=${2:-bin/osh}

  mkdir -p _tmp/lossless
  $sh --tool lossless-cat $path > _tmp/lossless/left.txt
  if diff -u $path _tmp/lossless/left.txt; then
	  echo "$path"
  else
	  return 1
  fi
}

test-here-doc() {
  _compare test/lossless/here-dq.sh
  _compare test/lossless/here-sq.sh

  # Hard test case!
  _compare test/lossless/here-multiple.sh

  # This is a known exception to the lossless invariant.  The leading tabs aren't
  # preserved, because we don't need them for ysh-ify translation.
  _compare test/lossless/here-dq-indented.sh
}

test-tilde() {
  _compare test/lossless/tilde.sh
}

test-ysh() {
  for file in ysh/testdata/*.ysh test/lossless/*.ysh; do
    echo "--- $file"
    _compare $file $YSH
  done
}

test-ysh-strings() {
  # TODO: extract test cases from test/ysh-every-string.sh
	# This includes multi-line strings

  echo 
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

test-big-sh-files() {
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

  echo
  echo "$num_passed of $num_files files respect the lossless invariant"
}

test-do-lossless-flag() {

  local sh_array='a[x+1]=1'

  # This gives you arithmetic parsing
  $OSH -n -c "$sh_array"
  # This gives you a sh_lhs.UnparsedIndex token!
  $OSH --do-lossless -n -c "$sh_array"

  local backticks='`echo \`hostname\` zzz`'

  # This gives you NESTED Id.Left_Backtick and Id.Backtick_Right
  $OSH -n -c "$backticks"

  # This gives (an erroneous?) Lit_EscapedChar
  $OSH --do-lossless -n -c "$backticks"

	local here=_tmp/lossless-here.sh 
  cat >$here <<EOF
cat <<-'HERE'
	one     # tabs stripped
		two   # 2 tabs
	three
	HERE
EOF

  # TODO: May need to show difference with --tool tokens
  $OSH -n $here
  $OSH --do-lossless -n $here
}

run-for-release() {
  run-other-suite-for-release lossless run-test-funcs
}

soil-run() {
  run-test-funcs
}

run-cpp() {
  # Not automated now, but it speeds things up

  local variant=opt  # also asan, ubsan

  local osh=_bin/cxx-$variant/osh
  local ysh=_bin/cxx-$variant/ysh

  ninja $osh $ysh

  OSH=$osh YSH=$ysh run-test-funcs
}

"$@"

#!/usr/bin/env bash
#
# Usage:
#   demo/ninja.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

test-ninja-quoting() {
  touch _tmp/{in1,in2}
  ninja -f demo/demo.ninja
}

test-shell() {
  # Same thing as Ninja

  out='_tmp/out1 _tmp/out2'
  in='_tmp/in1 _tmp/in2'
  empty=''
  sq="''"
  spaces='foo bar'

  local command="spec/bin/argv.py $out $empty $in $sq $spaces"

  # note the same!  Because it's word split, and then '' comes through as a
  # word
  $command

  # This is the same!
  eval "$command"
}

"$@"

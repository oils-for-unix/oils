#!/usr/bin/env bash

#### --debug-file
$SH --debug-file $TMP/debug.txt -c 'true'
grep 'Debug file' $TMP/debug.txt >/dev/null && echo yes
## stdout: yes

#### debug-completion option
set -o debug-completion
## status: 0

#### debug-completion from command line
$SH -o debug-completion
## status: 0

#### crash dump
rm -f $TMP/*.json
OSH_CRASH_DUMP_DIR=$TMP $SH -c '
g() {
  local glocal="glocal"
  echo $(( 1 / 0 ))
}
f() {
  local flocal="flocal"
  shift
  FOO=bar g
}
readonly array=(A B C)
f "${array[@]}"
' dummy a b c
echo status=$?
# Just check that we can parse it.  TODO: Test properties.
python -m json.tool $TMP/*.json > /dev/null
echo status=$?
## STDOUT:
status=1
status=0
## END

# NOTE: strict-arith has one case in arith.test.sh), strict-word-eval has a case in var-op-other.



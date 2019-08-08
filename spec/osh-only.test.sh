#!/usr/bin/env bash

#### --debug-file
$SH --debug-file $TMP/debug.txt -c 'true'
grep 'OSH started with' $TMP/debug.txt >/dev/null && echo yes
## stdout: yes

#### repr
x=42
repr x
echo status=$?
repr nonexistent
echo status=$?
## STDOUT:
x = (cell val:(value.Str s:42) exported:F readonly:F)
status=0
'nonexistent' is not defined
status=1
## END

#### repr on indexed array with hole
declare -a array
array[3]=42
repr array
## STDOUT:
array = (cell val:(value.MaybeStrArray strs:[_ _ _ 42]) exported:F readonly:F)
## END


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

#### crash dump with source
# TODO: The failure is not propagated through 'source'.  Failure only happens
# on 'errexit'.
#rm -f $TMP/*.json
OSH_CRASH_DUMP_DIR=$TMP $SH -c '
set -o errexit
source spec/testdata/crash.sh
'
echo status=$?

# Now try to parse crash dumps
set -o xtrace
set -o errexit
ok=0
for dump in $TMP/*.json; do
  # Workaround for test issue: release binaries leave empty files because they
  # don't have the json module.
  if test -s $dump; then  # non-empty
    python -m json.tool $dump > /dev/null
    echo "OK $dump" >&2
    (( ++ok ))
  fi
done
if test $ok -ge 1; then  # make sure we parsed at least once crash dump
  echo OK
fi
## STDOUT:
status=1
OK
## END

# NOTE: strict-arith has one case in arith.test.sh), strict-word-eval has a case in var-op-other.


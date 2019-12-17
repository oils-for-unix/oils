#!/usr/bin/env bash

#### --debug-file
$SH --debug-file $TMP/debug.txt -c 'true'
grep 'OSH started with' $TMP/debug.txt >/dev/null && echo yes
## stdout: yes

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
python2 -m json.tool $TMP/*.json > /dev/null
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

# NOTE: strict_arith has one case in arith.test.sh), strict_word-eval has a case in var-op-other.


#### help index
help index > $TMP/index.txt
echo index $?

help index command assign > $TMP/groups.txt
echo index groups $?

help index ZZZ > $TMP/index.txt
echo index ZZZ $?
## STDOUT:
index 0
index groups 0
index ZZZ 1
## END


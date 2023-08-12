
#### crash dump

rm -f $TMP/*.json

OILS_CRASH_DUMP_DIR=$TMP $SH -c '
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
OILS_CRASH_DUMP_DIR=$TMP $SH -c "
set -o errexit
source $REPO_ROOT/spec/testdata/crash.sh
"
echo crash status=$?

# Now try to parse crash dumps
set -o xtrace
set -o errexit

# Enumerate crash dumps
ok=0
for dump in $TMP/*.json; do
  # Workaround for test issue: release binaries leave empty files because they
  # don't have the json module.
  if test -s $dump; then  # non-empty
    python2 -m json.tool $dump > /dev/null
    echo "OK $dump" >&2
    (( ++ok ))
  fi
done

if test $ok -ge 1; then  # make sure we parsed at least once crash dump
  echo 'found crash dump'
fi

## STDOUT:
crash status=1
found crash dump
## END

# NOTE: strict_arith has one case in arith.test.sh), strict_word-eval has a case in var-op-other.


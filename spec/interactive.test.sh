#!/usr/bin/env bash
#

#### 'exit' in oshrc (regression)
cat >$TMP/oshrc <<EOF
echo one
exit 42
echo two
EOF
$SH --rcfile $TMP/oshrc -i -c 'echo hello'
## status: 42
## STDOUT:
one
## END
## N-I dash status: 2
## N-I dash stdout-json: ""
## N-I mksh status: 1
## N-I mksh stdout-json: ""

#### fatal errors continue

# NOTE: tried here doc, but sys.stdin.isatty() fails.  Could we fake it?
case "$SH" in
	*bash) FLAGS='--noprofile --norc';;
	*osh) FLAGS='--rcfile /dev/null';;
esac
$SH $FLAGS -i -c '
echo $(( 1 / 0 ))
echo one
exit 42
'
## status: 42
## STDOUT:
one
## END
## N-I dash status: 2
## N-I dash stdout-json: ""
## N-I mksh status: 1
## N-I mksh stdout-json: ""

#### interactive shell loads rcfile (when combined with -c)
$SH -c 'echo 1'
cat >$TMP/rcfile <<EOF
echo RCFILE
EOF
$SH --rcfile $TMP/rcfile -i -c 'echo 2'
## STDOUT:
1
RCFILE
2
## END
## N-I dash/mksh STDOUT:
1
## END
## N-I dash status: 2
## N-I mksh status: 1

#### interactive shell runs PROMPT_COMMAND after each command
TEST_CASE='PROMPT_COMMAND="echo hi"'
case $SH in
	*bash) echo "$TEST_CASE" | $SH --noprofile --norc -i;;
	*osh) $SH --rcfile /dev/null -i -c "$TEST_CASE";;
	*) $SH -i -c "$TEST_CASE";;
esac
## STDOUT:
hi
## N-I dash/mksh stdout-json: ""

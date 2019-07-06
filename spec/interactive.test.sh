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
$SH -i -c '
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


#!/bin/bash
#
# Usage:
#   ./sh-usage.test.sh <function name>

#### sh -c
$SH -c 'echo hi'
## stdout: hi
## status: 0

#### empty -c input
# had a bug here
$SH -c ''
## stdout-json: ""
## status: 0

#### sh +c is accepted
$SH +c 'echo hi'
## stdout: hi
## status: 0
## N-I mksh/yash stdout-json: ""
## N-I mksh/yash status: 127

#### empty stdin
# had a bug here
echo -n '' | $SH
## stdout-json: ""
## status: 0

#### shell obeys --help (regression for OSH)
n=$($SH --help | wc -l)
if test $n -gt 0; then
  echo yes
fi
## STDOUT:
yes
## END
## N-I dash/mksh stdout-json: ""

#### args are passed
$SH -c 'argv.py "$@"' dummy a b
## stdout: ['a', 'b']

#### args that look like flags are passed after script
script=$TMP/sh1.sh
echo 'argv.py "$@"' > $script
chmod +x $script
$SH $script --help --help -h
## stdout: ['--help', '--help', '-h']

#### args that look like flags are passed after -c
$SH -c 'argv.py "$@"' --help --help -h
## stdout: ['--help', '-h']

#### exit with explicit arg
exit 42
## status: 42

#### exit with no args
false
exit
## status: 1


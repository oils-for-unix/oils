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

#### --rcfile in non-interactive shell prints warnings
echo 'echo rc' > rc

$SH --rcfile rc -i </dev/null 2>interactive.txt
grep -q 'warning' interactive.txt
echo warned=$? >&2

$SH --rcfile rc </dev/null 2>non-interactive.txt
grep -q 'warning' non-interactive.txt
echo warned=$? >&2

head *interactive.txt

## STDERR:
warned=1
warned=0
## END
## N-I bash/dash/mksh STDERR:
warned=1
warned=1
## END

#### accepts -l flag
$SH -l -c 'exit 0'
## status: 0


#### accepts --login flag (dash and mksh don't accept long flags)
$SH --login -c 'exit 0'
## status: 0
## OK dash status: 2
## OK mksh status: 1

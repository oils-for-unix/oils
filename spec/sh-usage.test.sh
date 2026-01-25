## tags: interactive
## compare_shells: bash dash mksh zsh
## oils_failures_allowed: 0

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

#### sh - and sh -- stop flag processing
case $SH in zsh) exit ;; esac

echo 'echo foo' > foo.sh

$SH -x -v -- foo.sh

echo -  
echo - >& 2

$SH -x -v - foo.sh

## STDOUT:
foo
-
foo
## END
## STDERR:
echo foo
+ echo foo
-
echo foo
+ echo foo
## END

# I think it turns off -x -v with -
## BUG-2 mksh STDERR:
echo foo
+ echo foo
-
## END

# set -o verbose not implemented for now
## OK osh STDERR:
+ echo foo
-
+ echo foo
## END

## BUG zsh STDOUT:
## END
## BUG zsh STDERR:
## END

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
## N-I bash/dash/mksh/zsh STDERR:
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


#### osh --eval 
case $SH in bash|dash|mksh|zsh) exit ;; esac

echo 'echo one "$@"' > one.sh
echo 'echo fail "$@"; ( exit 42 )' > fail.sh

$SH --eval one.sh \
  -c 'echo status=$? flag -c "$@"' dummy x y z
echo

# Even though errexit is off, the shell exits if the last status of an --eval
# file was non-zero.

$SH --eval one.sh --eval fail.sh \
  -c 'echo status=$? flag -c "$@"' dummy x y z
echo status=$?

## STDOUT:
one x y z
status=0 flag -c x y z

one x y z
fail x y z
status=42 flag -c x y z
status=0
## END

## N-I bash/dash/mksh/zsh STDOUT:
## END

#### Set LC_ALL LC_CTYPE LC_COLLATE LANG - affects glob ?

# note: test/spec-common.sh sets LC_ALL
unset LC_ALL

touch _x_ _μ_

LC_ALL=C       $SH -c 'echo LC_ALL _?_'
LC_ALL=C.UTF-8 $SH -c 'echo LC_ALL _?_'
echo

LC_CTYPE=C       $SH -c 'echo LC_CTYPE _?_'
LC_CTYPE=C.UTF-8 $SH -c 'echo LC_CTYPE _?_'
echo

LC_COLLATE=C       $SH -c 'echo LC_COLLATE _?_'
LC_COLLATE=C.UTF-8 $SH -c 'echo LC_COLLATE _?_'
echo

LANG=C       $SH -c 'echo LANG _?_'
LANG=C.UTF-8 $SH -c 'echo LANG _?_'

## STDOUT:
LC_ALL _x_
LC_ALL _x_ _μ_

LC_CTYPE _x_
LC_CTYPE _x_ _μ_

LC_COLLATE _x_
LC_COLLATE _x_

LANG _x_
LANG _x_ _μ_
## END

## N-I dash/mksh STDOUT:
LC_ALL _x_
LC_ALL _x_

LC_CTYPE _x_
LC_CTYPE _x_

LC_COLLATE _x_
LC_COLLATE _x_

LANG _x_
LANG _x_
## END


#### LC_CTYPE=invalid

# note: test/spec-common.sh sets LC_ALL
unset LC_ALL

touch _x_ _μ_

{ LC_CTYPE=invalid $SH -c 'echo LC_CTYPE _?_' 
} 2> err.txt

#cat err.txt
wc -l err.txt

## STDOUT:
LC_CTYPE _x_
1 err.txt
## END

## N-I dash/mksh/zsh STDOUT:
LC_CTYPE _x_
0 err.txt
## END

#### sh -c -- 'echo hi' does not run anything (#2637)

$SH -c -z 'echo z'
if test $? -ne 0; then
  echo 'z failed'
fi
echo

$SH -c --- 'echo three'
if test $? -ne 0; then
  echo three failed
fi
echo

$SH -c -- 'echo two'
echo two=$?
echo

$SH -c - 'echo one'
echo one=$?
echo

$SH -c '' 'echo zero'
echo zero=$?
echo

# odd
$SH -c 'echo aa' 'echo bb'
echo aa=$?

## STDOUT:
z failed

three failed

two
two=0

one
one=0

zero=0

aa
aa=0
## END

## BUG ash STDOUT:
z failed

three

two
two=0

one
one=0

zero=0

aa
aa=0
## END

#### sh -c with multiple -- args

# variant of above case

$SH -c -- -- 'echo two'
echo status=$?

$SH -c -- -- -- 'echo two'
echo status=$?

$SH -c -z 'echo z'
if test $? -ne 0; then
  echo 'z failed'
fi

## STDOUT:
status=127
status=127
z failed
## END

#### sh -c with no arg after --

# variant of above case

$SH -c --
if test $? -ne 0; then
  echo failed
fi

$SH -c -
if test $? -ne 0; then
  echo failed
fi

## STDOUT:
failed
failed
## END

#### Other flag parsers are not affected by - rule

# -c is special, with quit_parsing_flags

echo 'foo-bar' | { read -d -; echo reply=$REPLY; }

## STDOUT:
reply=foo
## END
## N-I dash STDOUT:
reply=
## END

#### weird flag parsing -oo errexit noglob

prog='
case $- in
  *e*) echo e ;;
esac

case $- in
  *f*) echo f ;;
esac
'

# normal way
$SH -o errexit -o noglob -c "$prog"

# odd way
$SH -oo errexit noglob -c "$prog"

## STDOUT:
e
f
e
f
## END

## BUG mksh status: 1
## BUG mksh STDOUT:
e
f
## END

## BUG-2 zsh status: 1
## BUG-2 zsh STDOUT:
e
## END

#### 'sh -c -z' does not try to run -z

$SH -c -z
case $? in
  1) echo flag-parsing-error ;;
  2) echo flag-parsing-error ;;
  *) echo fail ;;
esac

$SH -c 'echo 0=$0 1=$1' -z
echo status=$?

$SH -c 'echo 0=$0 1=$1' foo -z
echo status=$?

## STDOUT:
flag-parsing-error
0=-z 1=
status=0
0=foo 1=-z
status=0
## END

#### sh -c -x 'echo hi' - order is reversed
case $SH in zsh) exit ;; esac  # different -x format

$SH -c -x 'echo hi'

# two flags before the command
$SH -c -x -e 'zz; true' 2> /dev/null
echo status=$?

## STDOUT:
hi
status=127
## END
## STDERR:
+ echo hi
## END

## OK zsh STDOUT:
## END
## OK zsh STDERR:
## END

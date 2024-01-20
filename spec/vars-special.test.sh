## oils_failures_allowed: 3
## compare_shells: dash bash mksh zsh


# NOTE:
# - $! is tested in background.test.sh
# - $- is tested in sh-options
#
# TODO: It would be nice to make a table, like:
#
# $$  $BASHPID  $PPID   $SHLVL   $BASH_SUBSHELL
#  X 
# (Subshell,  Command Sub,  Pipeline,  Spawn $0)
#
# And see whether the variable changed.

#### $PWD is set
# Just test that it has a slash for now.
echo $PWD | grep /
## status: 0

#### $PWD is not only set, but exported
env | grep PWD
## status: 0
## BUG mksh status: 1

#### $PATH is set if unset at startup

# Get absolute path before changing PATH
sh=$(which $SH)

old_path=$PATH
unset PATH

# BUG: when sh=bin/osh, we can't run bin/oils_for_unix.py
$sh -c 'echo $PATH' > path.txt

PATH=$old_path

# looks like PATH=/usr/bin:/bin for mksh, but more complicated for others
# cat path.txt

# should contain /usr/bin
if egrep -q '(^|:)/usr/bin($|:)' path.txt; then
  echo yes
fi

# should contain /bin
if egrep -q '(^|:)/bin($|:)' path.txt ; then
  echo yes
fi

## STDOUT:
yes
yes
## END


#### $HOME is NOT set
case $SH in *zsh) echo 'zsh sets HOME'; exit ;; esac

home=$(echo $HOME)
test "$home" = ""
echo status=$?

env | grep HOME
echo status=$?

# not in interactive shell either
$SH -i -c 'echo $HOME' | grep /
echo status=$?

## STDOUT:
status=0
status=1
status=1
## END
## BUG zsh STDOUT:
zsh sets HOME
## END


#### $1 .. $9 are scoped, while $0 is not
fun() { echo $0 $1 $2 | sed -e 's/.*sh/sh/'; }
fun a b
## stdout: sh a b
## BUG zsh stdout: fun a b

#### $?
echo $?  # starts out as 0
sh -c 'exit 33'
echo $?
## STDOUT:
0
33
## END
## status: 0

#### $#
set -- 1 2 3 4
echo $#
## stdout: 4
## status: 0

#### $$ looks like a PID
# Just test that it has decimal digits
echo $$ | egrep '[0-9]+'
## status: 0

#### $$ doesn't change with subshell or command sub
# Just test that it has decimal digits
set -o errexit
die() {
  echo 1>&2 "$@"; exit 1
}
parent=$$
test -n "$parent" || die "empty PID in parent"
( child=$$
  test -n "$child" || die "empty PID in subshell"
  test "$parent" = "$child" || die "should be equal: $parent != $child"
  echo 'subshell OK'
)
echo $( child=$$
        test -n "$child" || die "empty PID in command sub"
        test "$parent" = "$child" || die "should be equal: $parent != $child"
        echo 'command sub OK'
      )
exit 3  # make sure we got here
## status: 3
## STDOUT:
subshell OK
command sub OK
## END

#### $BASHPID DOES change with subshell and command sub
set -o errexit
die() {
  echo 1>&2 "$@"; exit 1
}
parent=$BASHPID
test -n "$parent" || die "empty BASHPID in parent"
( child=$BASHPID
  test -n "$child" || die "empty BASHPID in subshell"
  test "$parent" != "$child" || die "should not be equal: $parent = $child"
  echo 'subshell OK'
)
echo $( child=$BASHPID
        test -n "$child" || die "empty BASHPID in command sub"
        test "$parent" != "$child" ||
          die "should not be equal: $parent = $child"
        echo 'command sub OK'
      )
exit 3  # make sure we got here

# mksh also implements BASHPID!

## status: 3
## STDOUT:
subshell OK
command sub OK
## END
## N-I dash/zsh status: 1
## N-I dash/zsh stdout-json: ""

#### Background PID $! looks like a PID
sleep 0.01 &
pid=$!
wait
echo $pid | egrep '[0-9]+' >/dev/null
echo status=$?
## stdout: status=0

#### $PPID
echo $PPID | egrep '[0-9]+'
## status: 0

# NOTE: There is also $BASHPID

#### $PIPESTATUS
echo hi | sh -c 'cat; exit 33' | wc -l >/dev/null
argv.py "${PIPESTATUS[@]}"
## status: 0
## STDOUT:
['0', '33', '0']
## END
## N-I dash stdout-json: ""
## N-I dash status: 2
## N-I zsh STDOUT:
['']
## END

#### $RANDOM
expr $0 : '.*/osh$' && exit 99  # Disabled because of spec-runner.sh issue
echo $RANDOM | egrep '[0-9]+'
## status: 0
## N-I dash status: 1

#### $UID and $EUID
# These are both bash-specific.
set -o errexit
echo $UID | egrep -o '[0-9]+' >/dev/null
echo $EUID | egrep -o '[0-9]+' >/dev/null
echo status=$?
## stdout: status=0
## N-I dash/mksh stdout-json: ""
## N-I dash/mksh status: 1

#### $OSTYPE is non-empty
test -n "$OSTYPE"
echo status=$?
## STDOUT:
status=0
## END
## N-I dash/mksh STDOUT:
status=1
## END

#### $HOSTNAME
test "$HOSTNAME" = "$(hostname)"
echo status=$?
## STDOUT:
status=0
## END
## N-I dash/mksh/zsh STDOUT:
status=1
## END

#### $LINENO is the current line, not line of function call
echo $LINENO  # first line
g() {
  argv.py $LINENO  # line 3
}
f() {
  argv.py $LINENO  # line 6
  g
  argv.py $LINENO  # line 8
}
f
## STDOUT: 
1
['6']
['3']
['8']
## END
## BUG zsh STDOUT: 
1
['1']
['1']
['3']
## END
## BUG dash STDOUT: 
1
['2']
['2']
['4']
## END

#### $LINENO in "bare" redirect arg (bug regression)
filename=$TMP/bare3
rm -f $filename
> $TMP/bare$LINENO
test -f $filename && echo written
echo $LINENO
## STDOUT: 
written
5
## END
## BUG zsh STDOUT: 
## END

#### $LINENO in redirect arg (bug regression)
filename=$TMP/lineno_regression3
rm -f $filename
echo x > $TMP/lineno_regression$LINENO
test -f $filename && echo written
echo $LINENO
## STDOUT: 
written
5
## END

#### $LINENO in [[
echo one
[[ $LINENO -eq 2 ]] && echo OK
## STDOUT:
one
OK
## END
## N-I dash status: 127
## N-I dash stdout: one
## N-I mksh status: 1
## N-I mksh stdout: one

#### $LINENO in ((
echo one
(( x = LINENO ))
echo $x
## STDOUT:
one
2
## END
## N-I dash stdout-json: "one\n\n"

#### $LINENO in for loop
# hm bash doesn't take into account the word break.  That's OK; we won't either.
echo one
for x in \
  $LINENO zzz; do
  echo $x
done
## STDOUT:
one
2
zzz
## END
## OK mksh STDOUT:
one
1
zzz
## END

#### $LINENO in other for loops
set -- a b c
for x; do
  echo $LINENO $x
done
## STDOUT:
3 a
3 b
3 c
## END

#### $LINENO in for (( loop
# This is a real edge case that I'm not sure we care about.  We would have to
# change the span ID inside the loop to make it really correct.
echo one
for (( i = 0; i < $LINENO; i++ )); do
  echo $i
done
## STDOUT:
one
0
1
## END
## N-I dash stdout: one
## N-I dash status: 2
## BUG mksh stdout: one
## BUG mksh status: 1

#### $LINENO for assignment
a1=$LINENO a2=$LINENO
b1=$LINENO b2=$LINENO
echo $a1 $a2
echo $b1 $b2
## STDOUT:
1 1
2 2
## END

#### $LINENO in case
case $LINENO in
  1) echo 'got line 1' ;;
  *) echo line=$LINENO
esac
## STDOUT:
got line 1
## END
## BUG mksh STDOUT:
line=3
## END

#### $_ with simple command and evaluation

name=world
echo "hi $name"
echo "$_"
## STDOUT:
hi world
hi world
## END
## N-I dash/mksh STDOUT:
hi world

## END

#### $_ and ${_}
case $SH in (dash|mksh) exit ;; esac

_var=value

: 42
echo $_ $_var ${_}var

: 'foo'"bar"
echo $_

## STDOUT:
42 value 42var
foobar
## END
## N-I dash/mksh stdout-json: ""

#### $_ with word splitting
case $SH in (dash|mksh) exit ;; esac

setopt shwordsplit  # for ZSH

x='with spaces'
: $x
echo $_

## STDOUT:
spaces
## END
## N-I dash/mksh stdout-json: ""

#### $_ with pipeline and subshell
case $SH in (dash|mksh) exit ;; esac

shopt -s lastpipe

seq 3 | echo last=$_

echo pipeline=$_

( echo subshell=$_ )
echo done=$_

## STDOUT:
last=
pipeline=last=
subshell=pipeline=last=
done=pipeline=last=
## END

# very weird semantics for zsh!
## OK zsh STDOUT:
last=3
pipeline=last=3
subshell=
done=
## END

## N-I dash/mksh stdout-json: ""


#### $_ with && and ||
case $SH in (dash|mksh) exit ;; esac

echo hi && echo last=$_
echo and=$_

echo hi || echo last=$_
echo or=$_

## STDOUT:
hi
last=hi
and=last=hi
hi
or=hi
## END

## N-I dash/mksh stdout-json: ""

#### $_ is not reset with (( and [[

# bash is inconsistent because it does it for pipelines and assignments, but
# not (( and [[

case $SH in (dash|mksh) exit ;; esac

echo simple
(( a = 2 + 3 ))
echo "(( $_"

[[ a == *.py ]]
echo "[[ $_"

## STDOUT:
simple
(( simple
[[ (( simple
## END

## N-I dash/mksh stdout-json: ""


#### $_ with assignments, arrays, etc.
case $SH in (dash|mksh) exit ;; esac

: foo
echo "colon [$_]"

s=bar
echo "bare assign [$_]"

# zsh uses declare; bash uses s=bar
declare s=bar
echo "declare [$_]"

# zsh remains s:declare, bash resets it
a=(1 2)
echo "array [$_]"

# zsh sets it to declare, bash uses the LHS a
declare a=(1 2)
echo "declare array [$_]"

declare -g d=(1 2)
echo "declare flag [$_]"

## STDOUT:
colon [foo]
bare assign []
declare [s=bar]
array []
declare array [a]
declare flag [d]
## END

## OK zsh STDOUT:
colon [foo]
bare assign []
declare [declare]
array [declare [declare]]
declare array [declare]
declare flag [-g]
## END

## OK osh STDOUT:
colon [foo]
bare assign [colon [foo]]
declare [bare assign [colon [foo]]]
array [declare [bare assign [colon [foo]]]]
declare array [array [declare [bare assign [colon [foo]]]]]
declare flag [declare array [array [declare [bare assign [colon [foo]]]]]]
## END

## N-I dash/mksh stdout-json: ""

#### $_ with loop

case $SH in (dash|mksh) exit ;; esac

# zsh resets it when in a loop

echo init
echo begin=$_
for x in 1 2 3; do
  echo prev=$_
done

## STDOUT:
init
begin=init
prev=begin=init
prev=prev=begin=init
prev=prev=prev=begin=init
## END

## OK zsh STDOUT:
init
begin=init
prev=
prev=prev=
prev=prev=prev=
## END
## N-I dash/mksh stdout-json: ""


#### $_ is not undefined on first use
set -e

x=$($SH -u -c 'echo prev=$_')
echo status=$?

# bash and mksh set $_ to $0 at first; zsh is empty
#echo "$x"

## STDOUT:
status=0
## END

## N-I dash status: 2
## N-I dash stdout-json: ""

#### BASH_VERSION / OILS_VERSION
case $SH in
  bash)
    # BASH_VERSION=zz

    echo $BASH_VERSION | egrep -o '4\.4\.0' > /dev/null
    echo matched=$?
    ;;
  *osh)
    # note: version string is mutable like in bash.  I guess that's useful for
    # testing?  We might want a strict mode to eliminate that?

    echo $OILS_VERSION | egrep -o '[0-9]+\.[0-9]+\.' > /dev/null
    echo matched=$?
    ;;
  *)
    echo 'no version'
    ;;
esac
## STDOUT:
matched=0
## END
## N-I dash/mksh/zsh STDOUT:
no version
## END

#### seconds
case $SH in (dash) exit 0;; esac # dash does not support $SECONDS
secs=$SECONDS
if [[ $secs -ge 0 && -n "$secs" ]]; then
    exit 0
else
    exit 1
fi
## status: 0

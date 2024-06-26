## oils_failures_allowed: 6
## compare_shells: bash mksh ash

# Notes on bash semantics:
#
# https://www.gnu.org/software/bash/manual/bash.html
#
# The trap builtin (see Bourne Shell Builtins) allows an ERR pseudo-signal
# specification, similar to EXIT and DEBUG. Commands specified with an ERR trap
# are executed after a simple command fails, with a few exceptions. The ERR
# trap is not inherited by shell functions unless the -o errtrace option to the
# set builtin is enabled. 


#### trap can use original $LINENO

trap 'echo line=$LINENO' ERR

false
false
echo ok

## STDOUT:
line=3
line=4
ok
## END

#### trap ERR and if statement

if test -f /nope; then echo file exists; fi

trap 'echo err' ERR
#trap 'echo line=$LINENO' ERR

if test -f /nope; then echo file exists; fi

## STDOUT:
## END

#### trap ERR does not run in errexit situations

trap 'echo line=$LINENO' ERR

if false; then
  echo if
fi

while false; do
  echo while
done

until false; do
  echo until
  break
done

false || false || false

false && false && false

false; false; false

echo ok

## STDOUT:
until
line=16
line=20
line=20
line=20
ok
## END

#### trap ERR pipeline (also errexit)

# mksh and bash have different line numbers in this case
trap 'echo err' ERR
#trap 'echo line=$LINENO' ERR

# it's run for the last 'false'
false | false | false

# it's never run here
! true
! false

## STDOUT:
err
## END

#### trap ERR not active in shell functions in (bash behavior)

trap 'echo line=$LINENO' ERR

f() {
  false 
  true
}

f

## STDOUT:
## END

## N-I mksh STDOUT:
line=4
## END

#### trap ERR shell function - with errtrace

trap 'echo line=$LINENO' ERR

passing() {
  false  # line 4
  true
}

failing() {
  true
  false
}

passing
failing

set -o errtrace

echo 'now with errtrace'
passing
failing

echo ok

## STDOUT:
line=14
now with errtrace
line=4
line=10
line=20
ok
## END

## BUG mksh status: 1
## BUG mksh STDOUT:
line=4
line=10
## END


#### trap ERR with YSH proc

case $SH in bash|mksh|ash) exit ;; esac

# seems the same

shopt -s ysh:upgrade

proc abc { echo abc }
if test -f /nope { echo file exists }
trap abc ERR
if test -f /nope { echo file exists }

## STDOUT:
abc
## END

## N-I bash/mksh/ash STDOUT:
## END

#### trap ERR
err() {
  echo "err [$@] $?"
}
trap 'err x y' ERR 

echo A

false
echo B

( exit 42 )
echo C

trap - ERR  # disable trap

false
echo D

trap 'echo after errexit $?' ERR 

set -o errexit

( exit 99 )
echo E

## status: 99
## STDOUT:
A
err [x y] 1
B
err [x y] 42
C
D
after errexit 99
## END
## N-I dash STDOUT:
A
B
C
D
## END

#### trap ERR and pipelines (lastpipe and PIPESTATUS difference)
case $SH in ash) exit ;; esac

err() {
  echo "err [$@] status=$? [${PIPESTATUS[@]}]"
}
trap 'err' ERR 

echo A

false

# succeeds
echo B | grep B

# fails
echo C | grep zzz

echo D | grep zzz | cat

set -o pipefail
echo E | grep zzz | cat

trap - ERR  # disable trap

echo F | grep zz
echo ok

## STDOUT:
A
err [] status=1 [1]
B
err [] status=1 [0 1]
err [] status=1 [0 1 0]
ok
## END

# lastpipe semantics mean we get another call!
# also we don't set PIPESTATUS unless we get a pipeline

## OK osh STDOUT:
A
err [] status=1 []
B
err [] status=1 [0 0]
err [] status=1 [0 1]
err [] status=1 [0 1 0]
ok
## END

## N-I ash STDOUT:
## END

#### error in trap ERR (recursive)
case $SH in dash) exit ;; esac

err() {
  echo err status $?
  ( exit 2 )
}
trap 'err' ERR 

echo A
false
echo B

## STDOUT:
A
err status 1
B
## END
## N-I dash STDOUT:
## END


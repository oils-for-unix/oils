## oils_failures_allowed: 1
## compare_shells: dash bash mksh

# Notes on bash semantics:
#
# https://www.gnu.org/software/bash/manual/bash.html
#
# The trap builtin (see Bourne Shell Builtins) allows an ERR pseudo-signal
# specification, similar to EXIT and DEBUG. Commands specified with an ERR trap
# are executed after a simple command fails, with a few exceptions. The ERR
# trap is not inherited by shell functions unless the -o errtrace option to the
# set builtin is enabled. 


#### trap ERR and if statement

abc() { echo abc; }

if test -f /nope; then echo file exists; fi

trap abc ERR

if test -f /nope; then echo file exists; fi

## STDOUT:
## END

#### trap ERR with YSH proc

case $SH in dash|bash|mksh) exit ;; esac

# seems the same

shopt -s ysh:upgrade

proc abc { echo abc }
if test -f /nope { echo file exists }
trap abc ERR
if test -f /nope { echo file exists }

## STDOUT:
abc
## END

## N-I bash/dash/mksh STDOUT:
## END

#### trap 0 is equivalent to EXIT
# not sure why this is, but POSIX wants it.
trap 'echo EXIT' 0
echo status=$?
trap - EXIT
echo status=$?
## status: 0
## STDOUT:
status=0
status=0
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
case $SH in dash) exit ;; esac

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

## N-I dash STDOUT:
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


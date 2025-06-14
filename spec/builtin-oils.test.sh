## compare_shells: bash
## oils_failures_allowed: 1

#### invoke usage
case $SH in bash) exit ;; esac

invoke
echo status=$?

invoke --
echo status=$?

echo

invoke sleep 0
echo status=$?

invoke -- sleep 0
echo status=$?

invoke --builtin -- sleep 0
echo status=$?

## STDOUT:
status=2
status=2

status=0
status=0
status=0
## END
## N-I bash STDOUT:
## END

#### invoke nonexistent name
case $SH in bash) exit ;; esac

invoke zz
echo status=$?

invoke --builtin zz
echo status=$?

invoke --builtin -- zz
echo status=$?

## STDOUT:
status=1
status=1
status=1
## END
## N-I bash STDOUT:
## END

#### type and command builtin does not find private sleep, because it's not enabled

# Does Oils have __builtins__.special __builtins__.normal __builtins__.private
# perhaps?  That is another way of introspecting

remove-path() { sed 's;/.*/;;'; }

type -t sleep
type sleep | remove-path
echo

command -v sleep | remove-path

## STDOUT:
file
sleep is sleep

sleep
## END

#### but invoke --show finds the private builtin (alternative to type, command)
case $SH in bash) exit ;; esac

invoke --show sleep | grep private

## STDOUT:
sleep is a private shell builtin
## END

## N-I bash STDOUT:
## END

#### builtin sleep behaves like external sleep
case $SH in
  *osh) prefix='builtin' ;;
  *) prefix='' ;;
esac

$prefix sleep
if test "$?" != 0; then
  echo ok
fi

# This is different!  OSH is stricter
if false; then
$prefix sleep --
if test "$?" != 0; then
  echo ok
fi
fi

$prefix sleep -2
if test "$?" != 0; then
  echo ok
fi

$prefix sleep -- -2
if test "$?" != 0; then
  echo ok
fi

$prefix sleep zz
if test "$?" != 0; then
  echo ok
fi

$prefix sleep 0
echo status=$?

$prefix sleep -- 0
echo status=$?

$prefix sleep '0.0005'
echo status=$?

$prefix sleep '+0.0005'
echo status=$?

## STDOUT:
ok
ok
ok
ok
status=0
status=0
status=0
status=0
## END

#### builtin sleep usage errors
case $SH in bash) exit ;; esac

builtin sleep 0.5s
echo status=$?

builtin sleep 0.1 extra
echo status=$?

## STDOUT:
status=2
status=2
## END
## N-I bash STDOUT:
## END

#### sleep is still external

# should not work
builtin sleep --version
if test "$?" != '0'; then
  echo ok
fi

sleep --version | head -n 1 >& 2
echo status=$?

## STDOUT:
ok
status=0
## END

#### cat
case $SH in bash) exit ;; esac

enable --internal cat

# invoke --internal cat
# invoke -i cat

seq 3 | __cat

## STDOUT:
1
2
3
## END
## N-I bash STDOUT:
## END


#### readlink
case $SH in bash) exit ;; esac

echo TODO

# turn this into a builtin
# does that mean any builtin can be externalized?
# - [ aka test is a good candiate
# - we have stubs from true/false

## STDOUT:
## END

## N-I bash STDOUT:
## END

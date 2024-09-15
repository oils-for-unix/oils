## compare_shells: dash bash mksh ash
## oils_failures_allowed: 0

# builtin-trap.test.sh

#### trap accepts/ignores --
trap -- 'echo hi' EXIT
echo ok
## STDOUT:
ok
hi
## END

#### trap 'echo hi' KILL (regression test, caught by smoosh suite)
trap 'echo hi' 9
echo status=$?

trap 'echo hi' KILL
echo status=$?

trap 'echo hi' STOP
echo status=$?

trap 'echo hi' TERM
echo status=$?

## STDOUT:
status=0
status=0
status=0
status=0
## END
## OK osh STDOUT:
status=1
status=1
status=1
status=0
## END

#### Register invalid trap
trap 'foo' SIGINVALID
## status: 1

#### Remove invalid trap
trap - SIGINVALID
## status: 1

#### SIGINT and INT are aliases
trap - SIGINT
echo $?
trap - INT
echo $?
## STDOUT:
0
0
## END
## N-I dash STDOUT:
1
0
## END

#### Invalid trap invocation
trap 'foo'
echo status=$?
## STDOUT:
status=2
## END
## OK dash/ash STDOUT:
status=1
## END
## BUG mksh STDOUT:
status=0
## END

#### exit 1 when trap code string is invalid
# All shells spew warnings to stderr, but don't actually exit!  Bad!
trap 'echo <' EXIT
echo status=$?
## STDOUT:
status=1
## END

## BUG mksh status: 1
## BUG mksh STDOUT:
status=0
## END

## BUG ash status: 2
## BUG ash STDOUT:
status=0
## END

## BUG dash/bash status: 0
## BUG dash/bash STDOUT:
status=0
## END


#### trap EXIT calling exit
cleanup() {
  echo "cleanup [$@]"
  exit 42
}
trap 'cleanup x y z' EXIT
## stdout: cleanup [x y z]
## status: 42

#### trap EXIT return status ignored
cleanup() {
  echo "cleanup [$@]"
  return 42
}
trap 'cleanup x y z' EXIT
## stdout: cleanup [x y z]
## status: 0

#### trap EXIT with PARSE error
trap 'echo FAILED' EXIT
for
## stdout: FAILED
## status: 2
## OK mksh status: 1

#### trap EXIT with PARSE error and explicit exit
trap 'echo FAILED; exit 0' EXIT
for
## stdout: FAILED
## status: 0

#### trap EXIT with explicit exit
trap 'echo IN TRAP; echo $stdout' EXIT 
stdout=FOO
exit 42

## status: 42
## STDOUT:
IN TRAP
FOO
## END

#### trap EXIT with command sub / subshell / pipeline
trap 'echo EXIT TRAP' EXIT 

echo $(echo command sub)

( echo subshell )

echo pipeline | cat

## STDOUT:
command sub
subshell
pipeline
EXIT TRAP
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

#### trap 1 is equivalent to SIGHUP; HUP is equivalent to SIGHUP
trap 'echo HUP' SIGHUP
echo status=$?
trap 'echo HUP' HUP
echo status=$?
trap 'echo HUP' 1
echo status=$?
trap - HUP
echo status=$?
## status: 0
## STDOUT:
status=0
status=0
status=0
status=0
## END
## N-I dash STDOUT:
status=1
status=0
status=0
status=0
## END

#### eval in the exit trap (regression for issue #293)
trap 'eval "echo hi"' 0
## STDOUT:
hi
## END


#### exit codes for traps are isolated

trap 'echo USR1 trap status=$?; ( exit 42 )' USR1

echo before=$?

# Equivalent to 'kill -USR1 $$' except OSH doesn't have "kill" yet.
# /bin/kill doesn't exist on Debian unless 'procps' is installed.
sh -c "kill -USR1 $$"
echo after=$?

## STDOUT:
before=0
USR1 trap status=0
after=0
## END

#### traps are cleared in subshell (started with &)

# Test with SIGURG because the default handler is SIG_IGN
#
# If we use SIGUSR1, I think the shell reverts to killing the process

# https://man7.org/linux/man-pages/man7/signal.7.html

trap 'echo SIGURG' URG

kill -URG $$

# Hm trap doesn't happen here
{ echo begin child; sleep 0.1; echo end child; } &
kill -URG $!
wait
echo "wait status $?"

# In the CI, mksh sometimes gives:
#
# USR1
# begin child
# done
# 
# leaving off 'end child'.  This seems like a BUG to me?

## STDOUT:
SIGURG
begin child
end child
wait status 0
## END

#### trap USR1, sleep, SIGINT: non-interactively

$REPO_ROOT/spec/testdata/builtin-trap-usr1.sh

## STDOUT:
usr1
status=0
## END

#### trap INT, sleep, SIGINT: non-interactively

# mksh behaves differently in CI -- maybe when it's not connected to a
# terminal?
case $SH in mksh) echo mksh; exit ;; esac

$REPO_ROOT/spec/testdata/builtin-trap-int.sh

## STDOUT:
status=0
## END

## OK mksh STDOUT:
mksh
## END

# Not sure why other shells differ here, but running the trap is consistent
# with interactive cases in test/bugs.sh

## OK osh STDOUT:
int
status=0
## END

#### trap EXIT, sleep, SIGINT: non-interactively

$REPO_ROOT/spec/testdata/builtin-trap-exit.sh

## STDOUT:
on exit
status=0
## END

#### Remove trap with an unsigned integer

$SH -e -c '
trap "echo noprint" EXIT
trap 0 EXIT
echo ok0
'
echo

$SH -e -c '
trap "echo noprint" EXIT
trap " 42 " EXIT
echo ok42space
'
echo

# corner case: sometimes 07 is treated as octal, but not here
$SH -e -c '
trap "echo noprint" EXIT
trap 07 EXIT
echo ok07
'
echo

$SH -e -c '
trap "echo trap-exit" EXIT
trap -1 EXIT
echo bad
'
if test $? -ne 0; then
  echo failure
fi

## STDOUT:
ok0

ok42space

ok07

trap-exit
failure
## END

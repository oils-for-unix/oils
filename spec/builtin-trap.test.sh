# builtin-trap.test.sh

#### trap -l
trap -l | grep INT >/dev/null
## status: 0
## N-I dash/mksh status: 1

#### trap accepts/ignores --
trap -- 'echo hi' EXIT
echo done
## STDOUT:
done
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

#### trap -p
trap 'echo exit' EXIT
trap -p | grep EXIT >/dev/null
## status: 0
## N-I dash/mksh status: 1

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
## stdout: status=2
## OK dash stdout: status=1
## BUG mksh stdout: status=0

#### exit 1 when trap code string is invalid
# All shells spew warnings to stderr, but don't actually exit!  Bad!
trap 'echo <' EXIT
echo status=$?
## stdout: status=1
## BUG mksh status: 1
## BUG mksh stdout: status=0
## BUG dash/bash status: 0
## BUG dash/bash stdout: status=0

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

#### trap exit bug regression
trap 'echo IN TRAP; echo $stdout' EXIT 
stdout=FOO
exit

## STDOUT:
IN TRAP
FOO
## END

#### trap DEBUG
debuglog() {
  echo "debuglog [$@]"
}
trap 'debuglog x y' DEBUG
echo 1
echo 2
## STDOUT:
debuglog [x y]
1
debuglog [x y]
2
## END
## N-I dash/mksh STDOUT:
1
2
## END

#### trap DEBUG and pipeline
case $SH in (dash|mksh) exit 1 ;; esac

debuglog() {
  echo "  [$@]"
}
trap 'debuglog $LINENO' DEBUG

# gets run for each one of these
{ echo a; echo b; }

# only run for the last one
{ echo x; echo y; } | wc -l

# gets run for both of these
date | wc -l

date |
  wc -l

## STDOUT:
  [6]
a
  [6]
b
  [7]
2
  [8]
  [8]
1
  [9]
  [10]
1
## END
## N-I dash/mksh status: 1
## N-I dash/mksh stdout-json: ""


#### trap DEBUG with compound commands
case $SH in (dash|mksh) exit 1 ;; esac

# I'm not sure if the observed behavior actually matches the bash documentation
# ...
#
# https://www.gnu.org/software/bash/manual/html_node/Bourne-Shell-Builtins.html#Bourne-Shell-Builtins
#
# "If a sigspec is DEBUG, the command arg is executed before every simple 
# command, for command, case command, select command, every arithmetic for
# command, and before the first command executes in a shell function."

debuglog() {
  echo "  [$@]"
}
trap 'debuglog $LINENO' DEBUG

f() {
  local mylocal=1
  for i in "$@"; do
    export i=$i
  done
}

echo '-- assign --'
g=1   # executes ONCE here

echo '-- function call --'
f A B C  # executes ONCE here, but does NOT go into th efunction call


echo '-- for --'
# why does it execute twice here?  because of the for loop?  That's not a
# simple command.
for i in 1 2; do
  echo for1 $i
  echo for2 $i
done

echo '-- while --'
i=0
while (( i < 2 )); do
  echo while1 
  echo while2
  (( i++ ))
done

echo '-- if --'
if true; then
  echo IF
fi

echo '-- case --'
case x in
  (x)
    echo CASE
esac

## STDOUT:
  [12]
-- assign --
  [13]
  [14]
-- function call --
  [15]
  [16]
-- for --
  [17]
  [18]
for1 1
  [19]
for2 1
  [17]
  [18]
for1 2
  [19]
for2 2
  [21]
-- while --
  [22]
  [23]
  [24]
while1
  [25]
while2
  [26]
  [23]
  [24]
while1
  [25]
while2
  [26]
  [23]
  [28]
-- if --
  [29]
  [30]
IF
  [32]
-- case --
  [33]
  [35]
CASE
## END
## N-I dash/mksh status: 1
## N-I dash/mksh stdout-json: ""


#### trap RETURN
profile() {
  echo "profile [$@]"
}
g() {
  echo --
  echo g
  echo --
  return
}
f() {
  echo --
  echo f
  echo --
  g
}
# RETURN trap doesn't fire when a function returns, only when a script returns?
# That's not what the manual syas.
trap 'profile x y' RETURN
f
. $REPO_ROOT/spec/testdata/return-helper.sh
## status: 42
## STDOUT:
--
f
--
--
g
--
return-helper.sh
profile [x y]
## END
## N-I dash/mksh STDOUT:
--
f
--
--
g
--
return-helper.sh
## END

#### trap ERR and disable it
err() {
  echo "err [$@] $?"
}
trap 'err x y' ERR 
echo 1
false
echo 2
trap - ERR  # disable trap
false
echo 3
## STDOUT:
1
err [x y] 1
2
3
## END
## N-I dash STDOUT:
1
2
3
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

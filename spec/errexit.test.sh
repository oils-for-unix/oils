#
# Usage:
#   ./errexit.test.sh <function name>

#### errexit aborts early
set -o errexit
false
echo done
## stdout-json: ""
## status: 1

#### errexit for nonexistent command
set -o errexit
nonexistent__ZZ
echo done
## stdout-json: ""
## status: 127

#### errexit aborts early on pipeline
set -o errexit
echo hi | grep nonexistent
echo two
## stdout-json: ""
## status: 1

#### errexit with { }
# This aborts because it's not part of an if statement.
set -o errexit
{ echo one; false; echo two; }
## stdout: one
## status: 1

#### errexit with if and { }
set -o errexit
if { echo one; false; echo two; }; then
  echo three
fi
echo four
## status: 0
## STDOUT:
one
two
three
four
## END

#### errexit with ||
set -o errexit
echo hi | grep nonexistent || echo ok
## stdout: ok
## status: 0

#### errexit with &&
set -o errexit
echo ok && echo hi | grep nonexistent 
## stdout: ok
## status: 1

#### errexit test && -- from gen-module-init
set -o errexit
test "$mod" = readline && echo "#endif"
echo status=$?
## stdout: status=1

#### errexit test && and fail
set -o errexit
test -n X && false
echo status=$?
## stdout-json: ""
## status: 1

#### errexit and loop
set -o errexit
for x in 1 2 3; do
  test $x = 2 && echo "hi $x"
done
## stdout: hi 2
## status: 1

#### errexit and brace group { }
set -o errexit
{ test no = yes && echo hi; }
echo status=$?
## stdout: status=1

#### errexit and time { }
set -o errexit
time false
echo status=$?
## status: 1

#### errexit with !
set -o errexit
echo one
! true
echo two
! false
echo three
## STDOUT:
one
two
three
## END

#### errexit with ! and ;
# AST has extra Sentence nodes; there was a REGRESSION here.
set -o errexit; echo one; ! true; echo two; ! false; echo three
## STDOUT:
one
two
three
## END

#### errexit with while/until
set -o errexit
while false; do
  echo ok
done
until false; do
  echo ok  # do this once then exit loop
  break
done
## stdout: ok
## status: 0

#### errexit with (( ))
# from http://mywiki.wooledge.org/BashFAQ/105, this changed between versions.
# ash says that 'i++' is not found, but it doesn't exit.  I guess this is the 
# subshell problem?
set -o errexit
i=0
(( i++ ))
echo done
## stdout-json: ""
## status: 1
## N-I dash/ash status: 127
## N-I dash/ash stdout-json: ""

#### errexit with subshell
set -o errexit
( echo one; false; echo two; )
echo three
## status: 1
## STDOUT:
one
## END

#### set -o errexit while it's being ignored (moot with strict_errexit)
set -o errexit
# osh aborts early here
if { echo 1; false; echo 2; set -o errexit; echo 3; false; echo 4; }; then
  echo 5;
fi
echo 6
false  # this is the one that makes shells fail
echo 7
## status: 1
## STDOUT:
1
2
3
4
5
6
## END

#### set +o errexit while it's being ignored (moot with strict_errexit)
set -o errexit
if { echo 1; false; echo 2; set +o errexit; echo 3; false; echo 4; }; then
  echo 5;
fi
echo 6
false  # does NOT fail, because we restored it.
echo 7
## STDOUT:
1
2
3
4
5
6
7
## END

#### set +o errexit with 2 levels of ignored
set -o errexit
if { echo 1; ! set +o errexit; echo 2; }; then
  echo 3
fi
echo 6
false
echo 7

## STDOUT:
1
2
3
6
7
## END

#### setting errexit in a subshell works but doesn't affect parent shell
( echo 1; false; echo 2; set -o errexit; echo 3; false; echo 4; )
echo 5
false
echo 6
## STDOUT:
1
2
3
5
6
## END

#### set errexit while it's ignored in a subshell (moot with strict_errexit)
set -o errexit
if ( echo 1; false; echo 2; set -o errexit; echo 3; false; echo 4 ); then
  echo 5;
fi
echo 6  # This is executed because the subshell just returns false
false 
echo 7
## status: 1
## STDOUT:
1
2
3
4
5
6
## END

#### shopt -s strict:all || true while errexit is on
set -o errexit
shopt -s strict:all || true
echo one
false  # fail
echo two
## status: 1
## STDOUT:
one
## END

#### errexit double guard
# OSH bug fix.  ErrExit needs a counter, not a boolean.
set -o errexit
if { ! false; false; true; } then
  echo true
fi
false
echo done
## status: 1
## STDOUT:
true
## END

#### background processes respect errexit
set -o errexit
{ echo one; false; echo two; exit 42; } &
wait $!
## status: 1
## STDOUT:
one
## END

#### pipeline process respects errexit
set -o errexit
# It is respected here.
{ echo one; false; echo two; } | cat

# Also respected here.
{ echo three; echo four; } | while read line; do
  echo "[$line]"
  false
done
echo four
## status: 1
## STDOUT:
one
[three]
## END

#### compound command
# case from
# https://lists.gnu.org/archive/html/bug-bash/2020-05/msg00066.html

set -o errexit

{ cat ; } < not_exist.txt   

echo status=$?
echo 'should not get here'
## status: 1
## stdout-json: ""
## BUG dash/bash/ash status: 0
## BUG bash/ash STDOUT:
status=1
should not get here
## END
## BUG dash STDOUT:
status=2
should not get here
## END

#### while loop
# case from
# https://lists.gnu.org/archive/html/bug-bash/2020-05/msg00066.html

set -o errexit

while read line; do
 echo $line
done < not_exist.txt   

echo status=$?
echo 'should not get here'
## status: 1
## stdout-json: ""
## BUG dash/bash/ash status: 0
## BUG bash/ash STDOUT:
status=1
should not get here
## END
## BUG dash STDOUT:
status=2
should not get here
## END

#### set -e enabled in function (regression)
foo() {
  set -e
  false
  echo "should be executed"
}
#foo && true
#foo || true

if foo; then
  true
fi

echo "should be executed"
## STDOUT:
should be executed
should be executed
## END

#### set -e in function #2
foo() {
  set -e
  false
  echo "should be executed"
}
! foo

echo "should be executed"
## BUG bash stdout-json: ""
## BUG bash status: 1
## STDOUT:
should be executed
should be executed
## END


#### Command sub exit code is lost
echo ft $(false) $(true)
echo status=$?

set -o errexit
shopt -s inherit_errexit || true

# This changes it
#shopt -s command_sub_errexit || true

echo f $(date %x)
echo status=$?

# compare with 
# x=$(date %x)         # FAILS
# local x=$(date %x)   # does NOT fail

echo ft $(false) $(true)
echo status=$?

## STDOUT:
ft
status=0
f
status=0
ft
status=0
## END


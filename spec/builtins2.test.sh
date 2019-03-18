#!/bin/bash

#### command -v
myfunc() { echo x; }
command -v echo
echo $?
command -v myfunc
echo $?
command -v nonexistent  # doesn't print anything
echo $?
command -v for
echo $?
## STDOUT:
echo
0
myfunc
0
1
for
0
## OK dash STDOUT:
echo
0
myfunc
0
127
for
0
## END

#### command -v with multiple names
# ALL FOUR SHELLS behave differently here!
#
# bash chooses to swallow the error!  We agree with zsh if ANY word lookup
# fails, then the whole thing fails.

myfunc() { echo x; }
command -v echo myfunc ZZZ for
echo status=$?

## STDOUT:
echo
myfunc
for
status=1
## BUG bash STDOUT:
echo
myfunc
for
status=0
## BUG dash STDOUT: 
echo
status=0
## OK mksh STDOUT: 
echo
myfunc
status=1
## END

#### command skips function lookup
seq() {
  echo "$@"
}
command  # no-op
seq 3
command seq 3
# subshell shouldn't fork another process (but we don't have a good way of
# testing it)
( command seq 3 )
## STDOUT:
3
1
2
3
1
2
3
## END

#### command command seq 3
command command seq 3
## STDOUT:
1
2
3
## END
## N-I zsh stdout-json: ""
## N-I zsh status: 127

#### command command -v seq
seq() {
  echo 3
}
command command -v seq
## stdout: seq
## N-I zsh stdout-json: ""
## N-I zsh status: 127

#### history usage
history
echo status=$?
history +5  # hm bash considers this valid
echo status=$?
history -5  # invalid flag
echo status=$?
history f 
echo status=$?
history too many args
echo status=$?
## status: 0
## STDOUT:
status=0
status=0
status=2
status=2
status=2
## END
## OK bash STDOUT:
status=0
status=0
status=2
status=1
status=1
## END
## BUG zsh/mksh STDOUT:
status=1
status=1
status=1
status=1
status=1
## END
## N-I dash STDOUT:
status=127
status=127
status=127
status=127
status=127
## END

#### builtin
cd () { echo "hi"; }
cd
builtin cd / && pwd
unset -f cd
## STDOUT:
hi
/
## N-I dash STDOUT:
hi
## N-I dash STDERR:
/bin/dash: 3: builtin: not found

#### builtin ls not found
builtin ls
## status: 1
## OK bash STDERR:
/bin/bash: line 1: builtin: ls: not a shell builtin
## OK zsh STDERR:
zsh: no such builtin: ls
## OK mksh STDERR:
/bin/mksh: <stdin>[1]: builtin: ls: not found
## N-I dash status: 127
## N-I dash STDERR:
/bin/dash: 1: builtin: not found
## OK osh STDERR:
osh: 1: builtin: ls: not a shell builtin

#### builtin no args
builtin
## status 0
## N-I dash STDERR:
/bin/dash: 1: builtin: not found
## N-I dash status: 127

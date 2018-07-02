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

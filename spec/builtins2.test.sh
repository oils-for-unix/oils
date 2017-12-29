#!/bin/bash

### command -v
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

### command -v with multiple names
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

### dirs builtin
cd /
dirs
# status: 0
## STDOUT:
/
## END
## N-I dash/mksh status: 127
## N-I dash/mksh stdout-json: ""

### dirs -c to clear the stack
set -o errexit
cd /
pushd /tmp >/dev/null  # zsh pushd doesn't print anything, but bash does
echo --
dirs
dirs -c
echo --
dirs
## status: 0
## STDOUT:
--
/tmp /
--
/tmp
## N-I dash/mksh status: 127
## N-I dash/mksh stdout-json: ""

### dirs -v to print numbered stack, one entry per line
set -o errexit
cd /
pushd /tmp >/dev/null
echo --
dirs -v
pushd /lib >/dev/null
echo --
dirs -v
## status: 0
## STDOUT:
--
 0  /tmp
 1  /
--
 0  /lib
 1  /tmp
 2  /
## END
#
#  zsh uses tabs
## OK zsh stdout-json: "--\n0\t/tmp\n1\t/\n--\n0\t/lib\n1\t/tmp\n2\t/\n"
#
## N-I dash/mksh status: 127
## N-I dash/mksh stdout-json: ""

### dirs -p to print one entry per line
set -o errexit
cd /
pushd /tmp >/dev/null
echo --
dirs -p
pushd /lib >/dev/null
echo --
dirs -p
## STDOUT:
--
/tmp
/
--
/lib
/tmp
/
## N-I dash/mksh status: 127
## N-I dash/mksh stdout-json: ""

### dirs -l to print in long format, no tilde prefix
# Can't use the OSH test harness for this because
# /home/<username> may be included in a path.
cd /
HOME=/tmp
mkdir -p $HOME/oil_test
pushd $HOME/oil_test >/dev/null
dirs
dirs -l
# status: 0
## STDOUT:
~/oil_test /
/tmp/oil_test /
## END

### dirs to print using tilde-prefix format
cd /
HOME=$TMP
mkdir -p $HOME/oil_test
pushd $HOME/oil_test >/dev/null
dirs
# stdout: ~/oil_test /
# status: 0

### dirs test of path alias `..`
cd /tmp
pushd .. >/dev/null
dirs
# stdout: / /tmp
# status: 0

### dirs test of path alias `.`
cd /tmp
pushd . >/dev/null
dirs
# stdout: /tmp /tmp
# status: 0

#!/bin/bash

#### pushd/popd
set -o errexit
cd /
pushd /tmp
echo -n pwd=; pwd
popd
echo -n pwd=; pwd
## status: 0
## STDOUT:
/tmp /
pwd=/tmp
/
pwd=/
## END
## OK zsh STDOUT:
pwd=/tmp
pwd=/
## END
## N-I dash/mksh status: 127
## N-I dash/mksh stdout-json: ""

#### popd usage error
pushd / >/dev/null
popd zzz
echo status=$?
## STDOUT:
status=2
## END
## BUG zsh STDOUT:
status=0
## END

#### popd returns error on empty directory stack
message=$(popd 2>&1)
echo $?
echo "$message" | grep -o "directory stack empty"
## STDOUT:
1
directory stack empty
## END

#### dirs builtin
cd /
dirs
## status: 0
## STDOUT:
/
## END

#### dirs -c to clear the stack
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
## END

#### dirs -v to print numbered stack, one entry per line
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

#### dirs -p to print one entry per line
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
## END

#### dirs -l to print in long format, no tilde prefix
# Can't use the OSH test harness for this because
# /home/<username> may be included in a path.
cd /
HOME=/tmp
mkdir -p $HOME/oil_test
pushd $HOME/oil_test >/dev/null
dirs
dirs -l
## status: 0
## STDOUT:
~/oil_test /
/tmp/oil_test /
## END

#### dirs to print using tilde-prefix format
cd /
HOME=/tmp
mkdir -p $HOME/oil_test
pushd $HOME/oil_test >/dev/null
dirs
## stdout: ~/oil_test /
## status: 0

#### dirs test converting true home directory to tilde
cd /
HOME=/tmp
mkdir -p $HOME/oil_test/$HOME
pushd $HOME/oil_test/$HOME >/dev/null
dirs
## stdout: ~/oil_test/tmp /
## status: 0

#### dirs don't convert to tilde when $HOME is substring
cd /
mkdir -p /tmp/oil_test
mkdir -p /tmp/oil_tests
HOME=/tmp/oil_test
pushd /tmp/oil_tests
dirs

#### dirs tilde test when $HOME is exactly $PWD
cd /
mkdir -p /tmp/oil_test
HOME=/tmp/oil_test
pushd $HOME
dirs
## status: 0
# zsh doesn't duplicate the stack I guess.
## OK zsh stdout-json: "~ /\n"
## STDOUT:
~ /
~ /
## END

#### dirs test of path alias `..`
cd /tmp
pushd .. >/dev/null
dirs
## stdout: / /tmp
## status: 0

#### dirs test of path alias `.`
cd /tmp
pushd . >/dev/null
dirs
## stdout: /tmp /tmp
## status: 0

#!/bin/bash

### command -v
myfunc() { echo x; }
command -v echo
echo $?
command -v myfunc
echo $?
command -v nonexistent  # doesn't print anything?
echo $?
command -v for
echo $?
# stdout-json: "echo\n0\nmyfunc\n0\n1\nfor\n0\n"
# OK dash stdout-json: "echo\n0\nmyfunc\n0\n127\nfor\n0\n"

### command -v with multiple names
# bash chooses to swallow the error!  We agree with zsh if ANY word lookup
# fails, then the whole thing fails.
# All four shells behave differently here!
myfunc() { echo x; }
command -v echo myfunc ZZZ for
echo status=$?
# stdout-json: "echo\nmyfunc\nfor\nstatus=1\n"
# BUG bash stdout-json: "echo\nmyfunc\nfor\nstatus=0\n"
# BUG dash stdout-json: "echo\nstatus=0\n"
# OK mksh stdout-json: "echo\nmyfunc\nstatus=1\n"

### dirs builtin
cd /
dirs
# stdout-json: "/\n"
# status: 0
# N-I dash/mksh status: 127
# N-I dash/mksh stdout-json: ""

### dirs -c to clear the stack
cd /
pushd /tmp >/dev/null  # zsh pushd doesn't print anything, but bash does
dirs
dirs -c
dirs
# stdout-json: "/tmp /\n/tmp\n"
# status: 0
# N-I dash/mksh status: 127
# N-I dash/mksh stdout-json: ""

### dirs -v to print numbered stack, one entry per line
cd /
pushd /tmp >/dev/null
dirs -v
pushd /lib >/dev/null
dirs -v
# stdout-json: " 0  /tmp\n 1  /\n 0  /lib\n 1  /tmp\n 2  /\n"
# status: 0
# zsh uses tabs
# OK zsh stdout-json: "0\t/tmp\n1\t/\n0\t/lib\n1\t/tmp\n2\t/\n"
# N-I dash/mksh status: 127
# N-I dash/mksh stdout-json: ""

### dirs -p to print one entry per line
cd /
pushd /tmp >/dev/null
dirs -p
pushd /lib >/dev/null
dirs -p
# stdout-json: "/tmp\n/\n/lib\n/tmp\n/\n"
# N-I dash/mksh status: 127
# N-I dash/mksh stdout-json: ""

### dirs -l to print in long format, no tilde prefix
# Can't use the OSH test harness for this because
# /home/<username> may be included in a path.
cd /
HOME=/tmp
mkdir -p $HOME/oil_test
pushd $HOME/oil_test >/dev/null
dirs
dirs -l
# stdout-json: "~/oil_test /\n/tmp/oil_test /\n"
# status: 0

### dirs to print using tilde-prefix format
cd /
HOME=$TMP
mkdir -p $HOME/oil_test
pushd $HOME/oil_test >/dev/null
dirs
# stdout-json: "~/oil_test /\n"
# status: 0

### dirs test of path alias `..`
cd /tmp
pushd .. >/dev/null
dirs
# stdout-json: "/ /tmp\n"
# status: 0

### dirs test of path alias `.`
cd /tmp
pushd . >/dev/null
dirs
# stdout-json: "/tmp /tmp\n"

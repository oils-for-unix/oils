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
dirs
# stdout-json: ""
# status: 0
# N-I dash/mksh status: 127
# N-I dash/mksh stdout-json: ""

### dirs -c
pushd /
dirs
dirs -c
dirs
# stdout-json: "/\n/\n"
# status: 0
# N-I dash/mksh status: 127
# N-I dash/mksh stdout-json: ""

### dirs -v
pushd /
dirs -v
pushd /
dirs -v
# stdout-json: "/\n 0 /\n/ /\n 0 /\n 1 /\n"
# status: 0
# N-I dash/mksh status: 127
# N-I dash/mksh stdout-json: ""

### dirs -p
pushd /
dirs -p
pushd /
dirs -p
# stdout-json: "/\n/\n/ /\n/\n/\n"
# N-I dash/mksh status: 127
# N-I dash/mksh stdout-json: ""

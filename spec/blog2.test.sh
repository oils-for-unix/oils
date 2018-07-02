#!/usr/bin/env bash
#
# Tests for the blog.
#

#### -a
[ -a ]
echo status=$?
## stdout: status=0

#### -a -a
[ -a -a ]
echo status=$?
## stdout: status=1

#### -a -a -a
[ -a -a -a ]
echo status=$?
## stdout: status=0
## BUG mksh stdout: status=2

#### -a -a -a -a
[ -a -a -a -a ]
echo status=$?
## stdout: status=1
## BUG bash stdout: status=2

#### -a -a -a -a -a
[ -a -a -a -a -a ]
echo status=$?
## stdout: status=1
## BUG dash/zsh stdout: status=0

#### -a -a -a -a -a -a
[ -a -a -a -a -a -a ]
echo status=$?
## stdout: status=2
## BUG dash/zsh stdout: status=1

#### -a -a -a -a -a -a -a
[ -a -a -a -a -a -a -a ]
echo status=$?
## stdout: status=1
## BUG bash stdout: status=2
## BUG dash/zsh stdout: status=0

#### -a -a -a -a -a -a -a -a
[ -a -a -a -a -a -a -a -a ]
echo status=$?
## stdout: status=1

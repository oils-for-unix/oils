#!/bin/bash
#
# Tests for the blog.
#
# Fun game: try to come up with an expression that behaves differently on ALL
# FOUR shells.

### ${##}
set -- $(seq 25)
echo ${##}
# stdout: 2

### ${###}
set -- $(seq 25)
echo ${###}
# stdout: 25

### ${####}
set -- $(seq 25)
echo ${####}
# stdout: 25

### ${##2}
set -- $(seq 25)
echo ${##2}
# stdout: 5

### ${###2}
set -- $(seq 25)
echo ${###2}
# stdout: 5
# BUG mksh stdout: 25

### ${1####}
set -- '####'
echo ${1####}
# stdout: ##

### ${1#'###'}
set -- '####'
echo ${1#'###'}
# stdout: #

### ${#1#'###'}
set -- '####'
echo ${#1#'###'}
# dash and zsh accept; mksh and bash don't
# OK dash stdout: 4
# OK zsh stdout: 1
# N-I bash/mksh stdout-json: ""

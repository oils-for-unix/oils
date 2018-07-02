#!/usr/bin/env bash

#### Remove const suffix
v=abcd
echo ${v%d} ${v%%cd}
## stdout: abc ab

#### Remove const prefix
v=abcd
echo ${v#a} ${v##ab}
## stdout: bcd cd

#### Remove const suffix is vectorized on user array
a=(1a 2a 3a)
argv.py ${a[@]%a}
## stdout: ['1', '2', '3']
## status: 0
## N-I dash/mksh stdout-json: ""
## N-I dash status: 2
## N-I mksh status: 1

#### Remove const suffix is vectorized on $@ array
set -- 1a 2a 3a
argv.py ${@%a}
## stdout: ['1', '2', '3']
## status: 0
## N-I dash stdout: ['1a', '2a', '3']
## N-I dash status: 0
## N-I mksh stdout-json: ""
## N-I mksh status: 1

#### Remove const suffix from undefined
echo ${undef%suffix}
## stdout:

#### Remove shortest glob suffix
v=aabbccdd
echo ${v%c*}
## stdout: aabbc

#### Remove longest glob suffix
v=aabbccdd
echo ${v%%c*}
## stdout: aabb

#### Remove shortest glob prefix
v=aabbccdd
echo ${v#*b}
## stdout: bccdd

#### Remove longest glob prefix
v=aabbccdd
echo ${v##*b}
## stdout: ccdd

#### Strip char class
v=abc
echo ${v%[[:alpha:]]}
## stdout: ab
## N-I mksh stdout: abc

#### Strip unicode prefix
# NOTE: LANG is set to utf-8.  Problem: there is no way to represent the
# invalid character!  Instead of stdout-json, how about stdout-bytes?
v='μ-'
echo ${v#?}  # ? is a glob that stands for one character
## stdout: -
## BUG dash/mksh stdout-repr: '\xbc-\n'
## BUG zsh stdout-repr: '\n'

#### Bug fix: Test that you can remove everything with glob
s='--x--'
argv.py "${s%%-*}" "${s%-*}" "${s#*-}" "${s##*-}"
## STDOUT:
['', '--x-', '-x--', '']
## END

#### Test that you can remove everything with const
s='abcd'
argv.py "${s%%abcd}" "${s%abcd}" "${s#abcd}" "${s##abcd}"
# failure case:
argv.py "${s%%abcde}" "${s%abcde}" "${s#abcde}" "${s##abcde}"
## STDOUT:
['', '', '', '']
['abcd', 'abcd', 'abcd', 'abcd']
## END




#!/bin/bash

### Remove const suffix
v=abcd
echo ${v%d} ${v%%cd}
# stdout: abc ab

### Remove const prefix
v=abcd
echo ${v#a} ${v##ab}
# stdout: bcd cd

### Remove vectorized const suffix
set -- 1a 2a 3a
argv.py ${@%a}
# stdout: ['1', '2', '3']
# N-I dash stdout: ['1a', '2a', '3']
# N-I mksh stdout-json: ""

### Remove const suffix from undefined
echo ${undef%suffix}
# stdout:

### Remove smallest glob suffix
v=aabbccdd
echo ${v%c*}
# stdout: aabbc

### Remove longest glob suffix
v=aabbccdd
echo ${v%%c*}
# stdout: aabb

### Remove smallest glob prefix
v=aabbccdd
echo ${v#*b}
# stdout: bccdd

### Remove longest glob prefix
v=aabbccdd
echo ${v##*b}
# stdout: ccdd


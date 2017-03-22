#!/bin/bash
#
# Test combination of var ops.

### String length
v=foo
echo ${#v}
# stdout: 3

### Length of undefined variable
echo ${#undef}
# stdout: 0

### Length of undefined variable with nounset
set -o nounset
echo ${#undef}
# status: 1
# OK dash status: 2

### Cannot take length of substring slice
# These are runtime errors, but we could make them parse time errors.
v=abcde
echo ${#v:1:3}
# status: 1
# N-I dash status: 0
# N-I dash stdout: 5

### Pattern replacement
v=abcde
echo ${v/c*/XX}
# stdout: abXX
# N-I dash status: 2
# N-I dash stdout-json: ""

### String slice
foo=abcdefg
echo ${foo:1:3}
# stdout: bcd
# N-I dash status: 2
# N-I dash stdout-json: ""

### Negative string slice
foo=abcdefg
echo ${foo: -4:3}
# stdout: def
# N-I dash status: 2
# N-I dash stdout-json: ""

### String slice with math
# I think this is the $(()) language inside?
i=1
foo=abcdefg
echo ${foo: i-3-2 : i + 2}
# stdout: def
# N-I dash status: 2
# N-I dash stdout-json: ""

#!/usr/bin/env bash
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

### Global Pattern replacement with /
s=xx_xx_xx
echo ${s/xx?/yy_} ${s//xx?/yy_}
# stdout: yy_xx_xx yy_yy_xx
# N-I dash status: 2
# N-I dash stdout-json: ""

### Left Anchored Pattern replacement with #
s=xx_xx_xx
echo ${s/?xx/_yy} ${s/#?xx/_yy}
# stdout: xx_yy_xx xx_xx_xx
# N-I dash status: 2
# N-I dash stdout-json: ""

### Right Anchored Pattern replacement with %
s=xx_xx_xx
echo ${s/?xx/_yy} ${s/%?xx/_yy}
# stdout: xx_yy_xx xx_xx_yy
# N-I dash status: 2
# N-I dash stdout-json: ""

### Replace char class
s=xx_xx_xx
echo ${s//[[:alpha:]]/y} ${s//[^[:alpha:]]/-}
# stdout: yy_yy_yy xx-xx-xx
# N-I mksh stdout: xx_xx_xx xx_xx_xx
# N-I dash status: 2
# N-I dash stdout-json: ""

### Pattern replacement ${v/} is not valid
v=abcde
echo -${v/}-
echo status=$?
# status: 2
# stdout-json: ""
# N-I dash status: 2
# N-I dash stdout-json: ""
# BUG bash/mksh status: 0
# BUG bash/mksh stdout-json: "-abcde-\nstatus=0\n"

### Pattern replacement ${v//} is not valid
v='a/b/c'
echo -${v//}-
echo status=$?
# status: 2
# stdout-json: ""
# N-I dash status: 2
# N-I dash stdout-json: ""
# BUG bash/mksh status: 0
# BUG bash/mksh stdout-json: "-a/b/c-\nstatus=0\n"

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

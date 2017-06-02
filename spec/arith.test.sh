#!/bin/bash
#
# Interesting interpretation of constants.
#
# "Constants with a leading 0 are interpreted as octal numbers. A leading ‘0x’
# or ‘0X’ denotes hexadecimal. Otherwise, numbers take the form [base#]n, where
# the optional base is a decimal number between 2 and 64 representing the
# arithmetic base, and n is a number in that base. If base# is omitted, then
# base 10 is used. When specifying n, the digits greater than 9 are represented
# by the lowercase letters, the uppercase letters, ‘@’, and ‘_’, in that order.
# If base is less than or equal to 36, lowercase and uppercase letters may be
# used interchangeably to represent numbers between 10 and 35. "
# 
# NOTE $(( 8#9 )) can fail, and this can be done at parse time...

### Add one to var
i=1
echo $(($i+1))
# stdout: 2

### $ is optional
i=1
echo $((i+1))
# stdout: 2

### Bizarre recursive evaluation rule
foo=5
bar=foo
spam=bar
eggs=spam
echo $((foo+1)) $((bar+1)) $((spam+1)) $((eggs+1))
# stdout: 6 6 6 6
# N-I dash stdout-json: ""
# N-I dash status: 2

### SimpleVarSub within arith
echo $(($j + 1))
# stdout: 1

### BracedVarSub within ArithSub
echo $((${j:-5} + 1))
# stdout: 6

### Arith word part
foo=1; echo $((foo+1))bar$(($foo+1))
# stdout: 2bar2

### Arith sub with word parts
# Making 13 from two different kinds of sub.  Geez.
echo $((1 + $(echo 1)${undefined:-3}))
# stdout: 14

### Constant with quotes like '1'
# NOTE: Compare with [[.  That is a COMMAND level expression, while this is a
# WORD level expression.
echo $(('1' + 2))
# status: 0
# N-I bash/zsh status: 1
# N-I dash status: 2

### Arith sub within arith sub
# This is unnecessary but works in all shells.
echo $((1 + $((2 + 3)) + 4))
# stdout: 10

### Backticks within arith sub
# This is unnecessary but works in all shells.
echo $((`echo 1` + 2))
# stdout: 3

### Invalid string to int
# bash, mksh, and zsh all treat strings that don't look like numbers as zero.
s=foo
echo $((s+5))
# OK dash stdout-json: ""
# OK dash status: 2
# OK bash/mksh/zsh/osh stdout: 5
# OK bash/mksh/zsh/osh status: 0

### Invalid string to int with strict-arith
set -o strict-arith || true
s=foo
echo $s
echo $((s+5))
# status: 1
# stdout-json: "foo\n"
# N-I bash status: 0
# N-I bash stdout-json: "foo\n5\n"
# N-I dash status: 2
# N-I dash stdout-json: ""
# N-I mksh status: 1
# N-I mksh stdout-json: ""
# N-I zsh status: 1
# N-I zsh stdout-json: ""

### Newline in the middle of expression
echo $((1
+ 2))
# stdout: 3

### Ternary operator
a=1
b=2
echo $((a>b?5:10))
# stdout: 10

### Preincrement
a=4
echo $((++a))
echo $a
# stdout-json: "5\n5\n"
# N-I dash status: 0
# N-I dash stdout-json: "4\n4\n"

### Postincrement
a=4
echo $((a++))
echo $a
# stdout-json: "4\n5\n"
# N-I dash status: 2
# N-I dash stdout-json: ""

### Comma operator (borrowed from C)
a=1
b=2
echo $((a,(b+1)))
# stdout: 3
# N-I dash status: 2
# N-I dash stdout-json: ""

### Mutating ops
a=4
echo $((a+=1))
echo $a
# stdout-json: "5\n5\n"

### Bitwise ops
echo $((1|2))
echo $((1&2))
echo $((~(1|2)))
# stdout-json: "3\n0\n-4\n"

### Unary minus and plus
a=1
b=3
echo $((- a + + b))
# stdout-json: "2\n"

### No floating point
echo $((1 + 2.3))
# status: 1
# OK dash status: 2
# BUG zsh status: 0

### Array indexing in arith
# zsh does 1-based indexing!
array=(1 2 3 4)
echo $((array[1] + array[2]*3))
# stdout: 11
# OK zsh stdout: 7
# N-I dash status: 2
# N-I dash stdout-json: ""

### Constants in base 36
echo $((36#a))-$((36#z))
# stdout: 10-35
# N-I dash stdout-json: ""
# N-I dash status: 2

### Constants in bases 2 to 64
# This is a truly bizarre syntax.  Oh it comes from zsh... which allows 36.
echo $((64#a))-$((64#z)), $((64#A))-$((64#Z)), $((64#@)), $(( 64#_ ))
# stdout: 10-35, 36-61, 62, 63
# N-I dash stdout-json: ""
# N-I dash status: 2
# N-I mksh/zsh stdout-json: ""
# N-I mksh/zsh status: 1

### Dynamic base constants
base=16
echo $(( ${base}#a ))
# stdout: 10
# N-I dash stdout-json: ""
# N-I dash status: 2

### Octal constant
echo $(( 011 ))
# stdout: 9
# N-I mksh/zsh stdout: 11

### Dynamic octal constant
zero=0
echo $(( ${zero}11 ))
# stdout: 9
# N-I mksh/zsh stdout: 11

### Dynamic hex constants
zero=0
echo $(( ${zero}xAB ))
# stdout: 171

### Dynamic var names!
foo=5
x=oo
echo $(( foo + f$x + 1 ))
# stdout: 11

### nounset with arithmetic
set -o nounset
x=$(( y + 5 ))
echo "should not get here: x=${x:-<unset>}"
# stdout-json: ""
# status: 1
# BUG dash/mksh/zsh stdout: should not get here: x=5
# BUG dash/mksh/zsh status: 0

### Integer Overflow
set -o nounset
echo $(( 999999 * 999999 * 999999 * 999999 ))
# stdout: 999996000005999996000001
# BUG dash/bash/zsh stdout: -1996229794797103359
# BUG mksh stdout: -15640831

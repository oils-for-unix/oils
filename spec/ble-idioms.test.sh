#!/usr/bin/env bash

#### recursive arith: one level
a='b=123'
echo $((a))
## stdout: 123
## N-I dash status: 2
## N-I dash stdout-json: ""
## N-I yash stdout: b=123

#### recursive arith: two levels
a='b=c' c='d=123'
echo $((a))
## stdout: 123
## N-I dash status: 2
## N-I dash stdout-json: ""
## N-I yash stdout: b=c

#### recursive arith: short circuit &&, ||
# Note: mksh R52 has a bug. Even though it supports a short circuit like
#   "echo $((cond&&(a=1)))", it doesn't work with "x=a=1; echo
#   $((cond&&x))", It is fixed in mksh R57.
# Note: "busybox sh" doesn't support short circuit.
a=b=123
echo $((1||a)):$((b))
echo $((0||a)):$((b))
c=d=321
echo $((0&&c)):$((d))
echo $((1&&c)):$((d))
## stdout-json: "1:0\n1:123\n0:0\n1:321\n"
## BUG mksh stdout-json: "1:123\n1:123\n0:321\n1:321\n"
## N-I ash stdout-json: "1:123\n1:123\n0:321\n1:321\n"
## N-I dash/yash status: 2
## N-I dash/yash stdout-json: "1:0\n"

#### recursive arith: short circuit ?:
# Note: "busybox sh" behaves strangely.
y=a=123 n=a=321
echo $((1?(y):(n))):$((a))
echo $((0?(y):(n))):$((a))
## stdout-json: "123:123\n321:321\n"
## BUG ash stdout-json: "123:123\n321:123\n"
## N-I dash status: 2
## N-I dash stdout-json: ""
## N-I yash stdout-json: "a=123:0\na=321:0\n"

#### recursive arith: side effects
# In Zsh and Busybox sh, the side effect of inner arithmetic
# evaluations seems to take effect only after the whole expressions in
# Zsh and busybox sh.
a='b=c' c='d=123'
echo $((a,d)):$((d))
## stdout: 123:123
## BUG zsh/ash stdout: 0:123
## N-I dash/yash status: 2
## N-I dash/yash stdout-json: ""

#### recursive arith: recursion
loop='i<=100&&(s+=i,i++,loop)' s=0 i=0
echo $((a=loop,s))
## stdout: 5050
## N-I mksh status: 1
## N-I mksh stdout-json: ""
## N-I ash/dash/yash status: 2
## N-I ash/dash/yash stdout-json: ""

#### recursive arith: array elements
text[1]='d=123'
text[2]='text[1]'
text[3]='text[2]'
echo $((a=text[3]))
## stdout: 123
## N-I ash/dash/yash status: 2
## N-I ash/dash/yash stdout-json: ""

#!/usr/bin/env bash

#### recursive arith: one level
shopt -s eval_unsafe_arith
a='b=123'
echo $((a))
## stdout: 123
## N-I dash status: 2
## N-I dash stdout-json: ""
## N-I yash stdout: b=123

#### recursive arith: two levels
shopt -s eval_unsafe_arith
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
shopt -s eval_unsafe_arith
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
shopt -s eval_unsafe_arith
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
shopt -s eval_unsafe_arith
a='b=c' c='d=123'
echo $((a,d)):$((d))
## stdout: 123:123
## BUG zsh/ash stdout: 0:123
## N-I dash/yash status: 2
## N-I dash/yash stdout-json: ""

#### recursive arith: recursion
shopt -s eval_unsafe_arith
loop='i<=100&&(s+=i,i++,loop)' s=0 i=0
echo $((a=loop,s))
## stdout: 5050
## N-I mksh status: 1
## N-I mksh stdout-json: ""
## N-I ash/dash/yash status: 2
## N-I ash/dash/yash stdout-json: ""

#### recursive arith: array elements
shopt -s eval_unsafe_arith
text[1]='d=123'
text[2]='text[1]'
text[3]='text[2]'
echo $((a=text[3]))
## stdout: 123
## N-I ash/dash/yash status: 2
## N-I ash/dash/yash stdout-json: ""

#### ble.sh (dynamic var name with prefix): assign
shopt -s parse_dynamic_arith  # for LHS

vec2_set () {
  local this=$1 x=$2 y=$3
  : $(( ${this}_x = $2 ))
  : $(( ${this}_y = y ))
}
vec2_set a 3 4
vec2_set b 5 12
echo a_x=$a_x a_y=$a_y
echo b_x=$b_x b_y=$b_y
## STDOUT:
a_x=3 a_y=4
b_x=5 b_y=12
## END

#### ble.sh (dynamic var name with prefix): read
shopt -s eval_unsafe_arith  # for RHS

vec2_load() {
  local this=$1
  x=$(( ${this}_x ))
  : $(( y = ${this}_y ))
}
a_x=12 a_y=34
vec2_load a
echo x=$x y=$y
## STDOUT:
x=12 y=34
## END

#### ble.sh (dynamic var name with prefix): copy/add
shopt -s parse_dynamic_arith  # for LHS
shopt -s eval_unsafe_arith  # for RHS

vec2_copy () {
  local this=$1 rhs=$2
  : $(( ${this}_x = $(( ${rhs}_x )) ))
  : $(( ${this}_y = ${rhs}_y ))
}
vec2_add () {
  local this=$1 rhs=$2
  : $(( ${this}_x += $(( ${rhs}_x )) ))
  : $(( ${this}_y += ${rhs}_y ))
}
a_x=3 a_y=4
b_x=4 b_y=20
vec2_copy c a
echo c_x=$c_x c_y=$c_y
vec2_add c b
echo c_x=$c_x c_y=$c_y
## STDOUT:
c_x=3 c_y=4
c_x=7 c_y=24
## END

#### is-array with ${var@a}
case $SH in (mksh|ash) exit 1 ;; esac

function ble/is-array { [[ ${!1@a} == *a* ]]; }

ble/is-array undef
echo undef $?

string=''
ble/is-array string
echo string $?

array=(one two three)
ble/is-array array
echo array $?
## STDOUT:
undef 1
string 1
array 0
## END
## N-I zsh/mksh/ash status: 1
## N-I zsh/mksh/ash stdout-json: ""

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
#   $((cond&&x))". It is fixed at least in mksh R57.
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
# evaluations seems to take effect only after the whole evaluation.
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

#### dynamic arith varname: assign
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

#### dynamic arith varname: read
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

#### dynamic arith varname: copy/add
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
case $SH in (mksh|ash|dash|yash) exit 1 ;; esac

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
## N-I zsh/mksh/ash/dash/yash status: 1
## N-I zsh/mksh/ash/dash/yash stdout-json: ""


#### [bash_unset] local-unset / dynamic-unset for localvar
unlocal() { unset -v "$1"; }

f1() {
  local v=local
  unset v
  echo "[$1,local,(unset)] v: ${v-(unset)}"
}
v=global
f1 global

f1() {
  local v=local
  unlocal v
  echo "[$1,local,(unlocal)] v: ${v-(unset)}"
}
v=global
f1 'global'

## STDOUT:
# bash-unset
#   local-unset   = value-unset
#   dynamic-unset = cell-unset
[global,local,(unset)] v: (unset)
[global,local,(unlocal)] v: global
## END

## OK osh/mksh/yash STDOUT:
# always-cell-unset
#   local-unset   = cell-unset
#   dynamic-unset = cell-unset
[global,local,(unset)] v: global
[global,local,(unlocal)] v: global
## END

## OK zsh/ash/dash STDOUT:
# always-value-unset
#   local-unset   = value-unset
#   dynamic-unset = value-unset
[global,local,(unset)] v: (unset)
[global,local,(unlocal)] v: (unset)
## END


#### [bash_unset] local-unset / dynamic-unset for localvar (mutated from tempenv)
unlocal() { unset -v "$1"; }

f1() {
  local v=local
  unset v
  echo "[$1,local,(unset)] v: ${v-(unset)}"
}
v=global
v=tempenv f1 'global,tempenv'

f1() {
  local v=local
  unlocal v
  echo "[$1,local,(unlocal)] v: ${v-(unset)}"
}
v=global
v=tempenv f1 'global,tempenv'

## STDOUT:
# bash-unset (bash-5.1)
#   local-unset   = local-unset
#   dynamic-unset = cell-unset
[global,tempenv,local,(unset)] v: (unset)
[global,tempenv,local,(unlocal)] v: global
## END

## BUG bash STDOUT:
# bash-unset (bash-4.3..5.0 bug)
[global,tempenv,local,(unset)] v: global
[global,tempenv,local,(unlocal)] v: global
## END

## OK osh/mksh/yash STDOUT:
# always-cell-unset
#   local-unset   = cell-unset
#   dynamic-unset = cell-unset
[global,tempenv,local,(unset)] v: tempenv
[global,tempenv,local,(unlocal)] v: tempenv
## END

## OK zsh/ash/dash STDOUT:
# always-value-unset
#   local-unset   = value-unset
#   dynamic-unset = value-unset
[global,tempenv,local,(unset)] v: (unset)
[global,tempenv,local,(unlocal)] v: (unset)
## END


#### [bash_unset] local-unset / dynamic-unset for tempenv
unlocal() { unset -v "$1"; }

f1() {
  unset v
  echo "[$1,(unset)] v: ${v-(unset)}"
}
v=global
v=tempenv f1 'global,tempenv'

f1() {
  unlocal v
  echo "[$1,(unlocal)] v: ${v-(unset)}"
}
v=global
v=tempenv f1 'global,tempenv'

## STDOUT:
# always-cell-unset, bash-unset
#   local-unset   = cell-unset
#   dynamic-unset = cell-unset
[global,tempenv,(unset)] v: global
[global,tempenv,(unlocal)] v: global
## END

## OK zsh/ash/dash/mksh STDOUT:
# always-value-unset, mksh-unset
#   local-unset   = value-unset
#   dynamic-unset = value-unset
[global,tempenv,(unset)] v: (unset)
[global,tempenv,(unlocal)] v: (unset)
## END

#### [bash_unset] function call with tempenv vs tempenv-eval
unlocal() { unset -v "$1"; }

f5() {
  echo "[$1] v: ${v-(unset)}"
  local v
  echo "[$1,local] v: ${v-(unset)}"
  ( unset v
    echo "[$1,local+unset] v: ${v-(unset)}" )
  ( unlocal v
    echo "[$1,local+unlocal] v: ${v-(unset)}" )
}
v=global
f5 'global'
v=tempenv f5 'global,tempenv'
v=tempenv eval 'f5 "global,tempenv,(eval)"'

## STDOUT:
# bash-unset (bash-5.1)
[global] v: global
[global,local] v: (unset)
[global,local+unset] v: (unset)
[global,local+unlocal] v: global
[global,tempenv] v: tempenv
[global,tempenv,local] v: tempenv
[global,tempenv,local+unset] v: (unset)
[global,tempenv,local+unlocal] v: global
[global,tempenv,(eval)] v: tempenv
[global,tempenv,(eval),local] v: tempenv
[global,tempenv,(eval),local+unset] v: (unset)
[global,tempenv,(eval),local+unlocal] v: tempenv
## END

## BUG bash STDOUT:
# bash-unset (bash-4.3..5.0 bug)
[global] v: global
[global,local] v: (unset)
[global,local+unset] v: (unset)
[global,local+unlocal] v: global
[global,tempenv] v: tempenv
[global,tempenv,local] v: tempenv
[global,tempenv,local+unset] v: global
[global,tempenv,local+unlocal] v: global
[global,tempenv,(eval)] v: tempenv
[global,tempenv,(eval),local] v: tempenv
[global,tempenv,(eval),local+unset] v: (unset)
[global,tempenv,(eval),local+unlocal] v: tempenv
## END

## OK ash STDOUT:
# always-value-unset x init.unset
[global] v: global
[global,local] v: (unset)
[global,local+unset] v: (unset)
[global,local+unlocal] v: (unset)
[global,tempenv] v: tempenv
[global,tempenv,local] v: tempenv
[global,tempenv,local+unset] v: (unset)
[global,tempenv,local+unlocal] v: (unset)
[global,tempenv,(eval)] v: tempenv
[global,tempenv,(eval),local] v: (unset)
[global,tempenv,(eval),local+unset] v: (unset)
[global,tempenv,(eval),local+unlocal] v: (unset)
## END

## OK zsh STDOUT:
# always-value-unset x init.empty
[global] v: global
[global,local] v: 
[global,local+unset] v: (unset)
[global,local+unlocal] v: (unset)
[global,tempenv] v: tempenv
[global,tempenv,local] v: 
[global,tempenv,local+unset] v: (unset)
[global,tempenv,local+unlocal] v: (unset)
[global,tempenv,(eval)] v: tempenv
[global,tempenv,(eval),local] v: 
[global,tempenv,(eval),local+unset] v: (unset)
[global,tempenv,(eval),local+unlocal] v: (unset)
## END

## OK dash STDOUT:
# always-value-unset x init.inherit
[global] v: global
[global,local] v: global
[global,local+unset] v: (unset)
[global,local+unlocal] v: (unset)
[global,tempenv] v: tempenv
[global,tempenv,local] v: tempenv
[global,tempenv,local+unset] v: (unset)
[global,tempenv,local+unlocal] v: (unset)
[global,tempenv,(eval)] v: tempenv
[global,tempenv,(eval),local] v: tempenv
[global,tempenv,(eval),local+unset] v: (unset)
[global,tempenv,(eval),local+unlocal] v: (unset)
## END

## OK osh/yash/mksh STDOUT:
# always-cell-unset x init.unset
[global] v: global
[global,local] v: (unset)
[global,local+unset] v: global
[global,local+unlocal] v: global
[global,tempenv] v: tempenv
[global,tempenv,local] v: (unset)
[global,tempenv,local+unset] v: tempenv
[global,tempenv,local+unlocal] v: tempenv
[global,tempenv,(eval)] v: tempenv
[global,tempenv,(eval),local] v: (unset)
[global,tempenv,(eval),local+unset] v: tempenv
[global,tempenv,(eval),local+unlocal] v: tempenv
## END


#### [bash_unset] localvar-inherit from tempenv
f1() {
  local v
  echo "[$1,(local)] v: ${v-(unset)}"
}
f2() {
  f1 "$1,(func)"
}
f3() {
  local v=local
  f1 "$1,local,(func)"
}
v=global

f1 'global'
v=tempenv f1 'global,tempenv'
(export v=global; f1 'xglobal')

f2 'global'
v=tempenv f2 'global,tempenv'
(export v=global; f2 'xglobal')

f3 'global'

## STDOUT:
# init.bash
#   init.unset   for local
#   init.inherit for tempenv
[global,(local)] v: (unset)
[global,tempenv,(local)] v: tempenv
[xglobal,(local)] v: (unset)
[global,(func),(local)] v: (unset)
[global,tempenv,(func),(local)] v: tempenv
[xglobal,(func),(local)] v: (unset)
[global,local,(func),(local)] v: (unset)
## END

## OK osh/mksh/yash STDOUT:
# init.unset
[global,(local)] v: (unset)
[global,tempenv,(local)] v: (unset)
[xglobal,(local)] v: (unset)
[global,(func),(local)] v: (unset)
[global,tempenv,(func),(local)] v: (unset)
[xglobal,(func),(local)] v: (unset)
[global,local,(func),(local)] v: (unset)
## END

## OK ash STDOUT:
# init.unset x tempenv-in-localctx
[global,(local)] v: (unset)
[global,tempenv,(local)] v: tempenv
[xglobal,(local)] v: (unset)
[global,(func),(local)] v: (unset)
[global,tempenv,(func),(local)] v: (unset)
[xglobal,(func),(local)] v: (unset)
[global,local,(func),(local)] v: (unset)
## END

## OK zsh STDOUT:
# init.empty
[global,(local)] v: 
[global,tempenv,(local)] v: 
[xglobal,(local)] v: 
[global,(func),(local)] v: 
[global,tempenv,(func),(local)] v: 
[xglobal,(func),(local)] v: 
[global,local,(func),(local)] v: 
## END

## OK dash STDOUT:
# init.inherit
[global,(local)] v: global
[global,tempenv,(local)] v: tempenv
[xglobal,(local)] v: global
[global,(func),(local)] v: global
[global,tempenv,(func),(local)] v: tempenv
[xglobal,(func),(local)] v: global
[global,local,(func),(local)] v: local
## END


#### [bash_unset] nested context by tempenv-eval
f1() {
  local v=local1
  echo "[$1,local1] v: ${v-(unset)}"
  v=tempenv2 eval '
    echo "[$1,local1,tempenv2,(eval)] v: ${v-(unset)}"
    local v=local2
    echo "[$1,local1,tempenv2,(eval),local2] v: ${v-(unset)}"
  '
  echo "[$1,local1] v: ${v-(unset)} (after)"
}
v=global
v=tempenv1 f1 global,tempenv1

## STDOUT:
# localvar-nest yes
[global,tempenv1,local1] v: local1
[global,tempenv1,local1,tempenv2,(eval)] v: tempenv2
[global,tempenv1,local1,tempenv2,(eval),local2] v: local2
[global,tempenv1,local1] v: local1 (after)
## END

## OK mksh/ash/dash/yash STDOUT:
# localvar-nest no
[global,tempenv1,local1] v: local1
[global,tempenv1,local1,tempenv2,(eval)] v: tempenv2
[global,tempenv1,local1,tempenv2,(eval),local2] v: local2
[global,tempenv1,local1] v: local2 (after)
## END

#### [bash_unset] local-unset / dynamic-unset for localvar on nested-context
unlocal() { unset -v "$1"; }

f2() {
  local v=local1
  v=tempenv2 eval '
    local v=local2
    (unset v  ; echo "[$1,local1,tempenv2,(eval),local2,(unset)] v: ${v-(unset)}")
    (unlocal v; echo "[$1,local1,tempenv2,(eval),local2,(unlocal)] v: ${v-(unset)}")
  '
}
v=global
v=tempenv1 f2 global,tempenv1

## STDOUT:
# bash-unset (bash-5.1)
[global,tempenv1,local1,tempenv2,(eval),local2,(unset)] v: (unset)
[global,tempenv1,local1,tempenv2,(eval),local2,(unlocal)] v: local1
## END

## BUG bash STDOUT:
# bash-unset (bash-4.3..5.0 bug)
[global,tempenv1,local1,tempenv2,(eval),local2,(unset)] v: local1
[global,tempenv1,local1,tempenv2,(eval),local2,(unlocal)] v: local1
## END

## OK zsh/ash/dash STDOUT:
# always-value-unset
[global,tempenv1,local1,tempenv2,(eval),local2,(unset)] v: (unset)
[global,tempenv1,local1,tempenv2,(eval),local2,(unlocal)] v: (unset)
## END

## OK osh STDOUT:
# always-cell-unset x localvar-tempenv-share
[global,tempenv1,local1,tempenv2,(eval),local2,(unset)] v: local1
[global,tempenv1,local1,tempenv2,(eval),local2,(unlocal)] v: local1
## END

## OK mksh/yash STDOUT:
# always-cell-unset (remove all localvar/tempenv)
[global,tempenv1,local1,tempenv2,(eval),local2,(unset)] v: tempenv1
[global,tempenv1,local1,tempenv2,(eval),local2,(unlocal)] v: tempenv1
## END

#### [bash_unset] dynamic-unset for nested localvars
unlocal() { unset -v "$1"; }

f3() {
  local v=local1
  v=tempenv2 eval '
    local v=local2
    v=tempenv3 eval "
      local v=local3
      echo \"[\$1/local1,tempenv2/local2,tempenv3/local3] v: \${v-(unset)}\"
      unlocal v
      echo \"[\$1/local1,tempenv2/local2,tempenv3/local3] v: \${v-(unset)} (unlocal 1)\"
      unlocal v
      echo \"[\$1/local1,tempenv2/local2,tempenv3/local3] v: \${v-(unset)} (unlocal 2)\"
      unlocal v
      echo \"[\$1/local1,tempenv2/local2,tempenv3/local3] v: \${v-(unset)} (unlocal 3)\"
      unlocal v
      echo \"[\$1/local1,tempenv2/local2,tempenv3/local3] v: \${v-(unset)} (unlocal 4)\"
    "
  '
}
v=global
v=tempenv1 f3 global,tempenv1

## STDOUT:
# cell-unset x localvar-tempenv-share x tempenv-in-localctx
[global,tempenv1/local1,tempenv2/local2,tempenv3/local3] v: local3
[global,tempenv1/local1,tempenv2/local2,tempenv3/local3] v: local2 (unlocal 1)
[global,tempenv1/local1,tempenv2/local2,tempenv3/local3] v: local1 (unlocal 2)
[global,tempenv1/local1,tempenv2/local2,tempenv3/local3] v: global (unlocal 3)
[global,tempenv1/local1,tempenv2/local2,tempenv3/local3] v: (unset) (unlocal 4)
## END

## OK zsh/ash/dash STDOUT:
# value-unset
[global,tempenv1/local1,tempenv2/local2,tempenv3/local3] v: local3
[global,tempenv1/local1,tempenv2/local2,tempenv3/local3] v: (unset) (unlocal 1)
[global,tempenv1/local1,tempenv2/local2,tempenv3/local3] v: (unset) (unlocal 2)
[global,tempenv1/local1,tempenv2/local2,tempenv3/local3] v: (unset) (unlocal 3)
[global,tempenv1/local1,tempenv2/local2,tempenv3/local3] v: (unset) (unlocal 4)
## END

## OK osh STDOUT:
# cell-unset x localvar-tempenv-share
[global,tempenv1/local1,tempenv2/local2,tempenv3/local3] v: local3
[global,tempenv1/local1,tempenv2/local2,tempenv3/local3] v: local2 (unlocal 1)
[global,tempenv1/local1,tempenv2/local2,tempenv3/local3] v: local1 (unlocal 2)
[global,tempenv1/local1,tempenv2/local2,tempenv3/local3] v: tempenv1 (unlocal 3)
[global,tempenv1/local1,tempenv2/local2,tempenv3/local3] v: global (unlocal 4)
## END

## OK yash STDOUT:
# cell-unset (remove all localvar)
[global,tempenv1/local1,tempenv2/local2,tempenv3/local3] v: local3
[global,tempenv1/local1,tempenv2/local2,tempenv3/local3] v: tempenv1 (unlocal 1)
[global,tempenv1/local1,tempenv2/local2,tempenv3/local3] v: global (unlocal 2)
[global,tempenv1/local1,tempenv2/local2,tempenv3/local3] v: (unset) (unlocal 3)
[global,tempenv1/local1,tempenv2/local2,tempenv3/local3] v: (unset) (unlocal 4)
## END

## OK mksh STDOUT:
# cell-unset (remove all localvar/tempenv) x tempenv-value-unset
[global,tempenv1/local1,tempenv2/local2,tempenv3/local3] v: local3
[global,tempenv1/local1,tempenv2/local2,tempenv3/local3] v: tempenv1 (unlocal 1)
[global,tempenv1/local1,tempenv2/local2,tempenv3/local3] v: (unset) (unlocal 2)
[global,tempenv1/local1,tempenv2/local2,tempenv3/local3] v: (unset) (unlocal 3)
[global,tempenv1/local1,tempenv2/local2,tempenv3/local3] v: (unset) (unlocal 4)
## END


#### [bash_unset] dynamic-unset for nested tempenvs
unlocal() { unset -v "$1"; }

f4_unlocal() {
  v=tempenv2 eval '
    v=tempenv3 eval "
      echo \"[\$1,tempenv2,tempenv3] v: \${v-(unset)}\"
      unlocal v
      echo \"[\$1,tempenv2,tempenv3] v: \${v-(unset)} (unlocal 1)\"
      unlocal v
      echo \"[\$1,tempenv2,tempenv3] v: \${v-(unset)} (unlocal 2)\"
      unlocal v
      echo \"[\$1,tempenv2,tempenv3] v: \${v-(unset)} (unlocal 3)\"
      unlocal v
      echo \"[\$1,tempenv2,tempenv3] v: \${v-(unset)} (unlocal 4)\"
    "
  '
}
v=global
v=tempenv1 f4_unlocal global,tempenv1

## STDOUT:
[global,tempenv1,tempenv2,tempenv3] v: tempenv3
[global,tempenv1,tempenv2,tempenv3] v: tempenv2 (unlocal 1)
[global,tempenv1,tempenv2,tempenv3] v: tempenv1 (unlocal 2)
[global,tempenv1,tempenv2,tempenv3] v: global (unlocal 3)
[global,tempenv1,tempenv2,tempenv3] v: (unset) (unlocal 4)
## END

## OK zsh/ash/dash/mksh STDOUT:
# value-unset, mksh-unset
[global,tempenv1,tempenv2,tempenv3] v: tempenv3
[global,tempenv1,tempenv2,tempenv3] v: (unset) (unlocal 1)
[global,tempenv1,tempenv2,tempenv3] v: (unset) (unlocal 2)
[global,tempenv1,tempenv2,tempenv3] v: (unset) (unlocal 3)
[global,tempenv1,tempenv2,tempenv3] v: (unset) (unlocal 4)
## END

## OK osh STDOUT:
# cell-unset
[global,tempenv1,tempenv2,tempenv3] v: tempenv3
[global,tempenv1,tempenv2,tempenv3] v: tempenv2 (unlocal 1)
[global,tempenv1,tempenv2,tempenv3] v: tempenv1 (unlocal 2)
[global,tempenv1,tempenv2,tempenv3] v: global (unlocal 3)
[global,tempenv1,tempenv2,tempenv3] v: (unset) (unlocal 4)
## END

## OK yash STDOUT:
# remove all tempenv3
[global,tempenv1,tempenv2,tempenv3] v: tempenv3
[global,tempenv1,tempenv2,tempenv3] v: (unset) (unlocal 1)
[global,tempenv1,tempenv2,tempenv3] v: (unset) (unlocal 2)
[global,tempenv1,tempenv2,tempenv3] v: (unset) (unlocal 3)
[global,tempenv1,tempenv2,tempenv3] v: (unset) (unlocal 4)
## END

#### [bash_unset] local-unset for nested tempenvs
f4_unset() {
  v=tempenv2 eval '
    v=tempenv3 eval "
      echo \"[\$1,tempenv2,tempenv3] v: \${v-(unset)}\"
      unset v
      echo \"[\$1,tempenv2,tempenv3] v: \${v-(unset)} (unset 1)\"
      unset v
      echo \"[\$1,tempenv2,tempenv3] v: \${v-(unset)} (unset 2)\"
      unset v
      echo \"[\$1,tempenv2,tempenv3] v: \${v-(unset)} (unset 3)\"
      unset v
      echo \"[\$1,tempenv2,tempenv3] v: \${v-(unset)} (unset 4)\"
    "
  '
}
v=global
v=tempenv1 f4_unset global,tempenv1

## STDOUT:
[global,tempenv1,tempenv2,tempenv3] v: tempenv3
[global,tempenv1,tempenv2,tempenv3] v: tempenv2 (unset 1)
[global,tempenv1,tempenv2,tempenv3] v: tempenv1 (unset 2)
[global,tempenv1,tempenv2,tempenv3] v: global (unset 3)
[global,tempenv1,tempenv2,tempenv3] v: (unset) (unset 4)
## END

## OK zsh/ash/dash/mksh/yash STDOUT:
# value-unset, mksh-unset, tempenv-value-unset?
[global,tempenv1,tempenv2,tempenv3] v: tempenv3
[global,tempenv1,tempenv2,tempenv3] v: (unset) (unset 1)
[global,tempenv1,tempenv2,tempenv3] v: (unset) (unset 2)
[global,tempenv1,tempenv2,tempenv3] v: (unset) (unset 3)
[global,tempenv1,tempenv2,tempenv3] v: (unset) (unset 4)
## END

## OK osh STDOUT:
# cell-unset
[global,tempenv1,tempenv2,tempenv3] v: tempenv3
[global,tempenv1,tempenv2,tempenv3] v: tempenv2 (unset 1)
[global,tempenv1,tempenv2,tempenv3] v: tempenv1 (unset 2)
[global,tempenv1,tempenv2,tempenv3] v: global (unset 3)
[global,tempenv1,tempenv2,tempenv3] v: (unset) (unset 4)
## END

## BUG yash STDOUT:
# value-unset? inconsistent with other test cases
[global,tempenv1,tempenv2,tempenv3] v: tempenv3
[global,tempenv1,tempenv2,tempenv3] v: (unset) (unset 1)
[global,tempenv1,tempenv2,tempenv3] v: (unset) (unset 2)
[global,tempenv1,tempenv2,tempenv3] v: (unset) (unset 3)
[global,tempenv1,tempenv2,tempenv3] v: (unset) (unset 4)
## END

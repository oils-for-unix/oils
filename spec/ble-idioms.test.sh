
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
#   $((cond&&x))". It is fixed at least in mksh R57.
# Note: "busybox sh" doesn't support short circuit.
a=b=123
echo $((1||a)):$((b))
echo $((0||a)):$((b))
c=d=321
echo $((0&&c)):$((d))
echo $((1&&c)):$((d))
## STDOUT:
1:0
1:123
0:0
1:321
## END

## BUG mksh/ash STDOUT:
1:123
1:123
0:321
1:321
## END

## N-I dash/yash status: 2
## N-I dash/yash STDOUT:
1:0
## END

#### recursive arith: short circuit ?:
# Note: "busybox sh" behaves strangely.
y=a=123 n=a=321
echo $((1?(y):(n))):$((a))
echo $((0?(y):(n))):$((a))
## STDOUT:
123:123
321:321
## END
## BUG ash STDOUT:
123:321
321:321
## END
## N-I dash status: 2
## N-I dash stdout-json: ""
## N-I yash STDOUT: 
a=123:0
a=321:0
## END

#### recursive arith: side effects
# In Zsh and Busybox sh, the side effect of inner arithmetic
# evaluations seems to take effect only after the whole evaluation.
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

#### dynamic arith varname: assign
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


#### Sparse array with big index

# TODO: more BashArray idioms / stress tests ?

a=()

if false; then
  # This takes too long!  # From Zulip
  i=$(( 0x0100000000000000 ))
else
  # smaller number that's OK
  i=$(( 0x0100000 ))
fi

a[i]=1

echo len=${#a[@]}

## STDOUT:
len=1
## END

## N-I ash status: 2
## N-I ash STDOUT:
## END

## BUG zsh STDOUT:
len=1048576
## END


#### shift unshift reverse

case $SH in mksh|ash) exit ;; esac

# https://github.com/akinomyoga/ble.sh/blob/79beebd928cf9f6506a687d395fd450d027dc4cd/src/util.sh#L578-L582

# @fn ble/array#unshift arr value...
function ble/array#unshift {
  builtin eval -- "$1=(\"\${@:2}\" \"\${$1[@]}\")"
}
# @fn ble/array#shift arr count
function ble/array#shift {
  # Note: Bash 4.3 以下では ${arr[@]:${2:-1}} が offset='${2'
  # length='-1' に解釈されるので、先に算術式展開させる。
  builtin eval -- "$1=(\"\${$1[@]:$((${2:-1}))}\")"
}
# @fn ble/array#reverse arr
function ble/array#reverse {
  builtin eval "
  set -- \"\${$1[@]}\"; $1=()
  local e$1 i$1=\$#
  for e$1; do $1[--i$1]=\"\$e$1\"; done"
}

a=( {1..6} )
echo "${a[@]}"

ble/array#shift a 1
echo "${a[@]}"

ble/array#shift a 2
echo "${a[@]}"

echo ---

ble/array#unshift a 99
echo "${a[@]}"

echo ---

# doesn't work in zsh!
ble/array#reverse a
echo "${a[@]}"


## STDOUT:
1 2 3 4 5 6
2 3 4 5 6
4 5 6
---
99 4 5 6
---
6 5 4 99
## END

## BUG zsh STDOUT:
1 2 3 4 5 6
2 3 4 5 6
4 5 6
---
99 4 5 6
---
5 4 99
## END

## N-I mksh/ash STDOUT:
## END


#### SparseArray Performance demo

case $SH in bash|zsh|mksh|ash) exit ;; esac

#pp test_ (a)

a=( foo {25..27} bar )

a[10]='sparse'

var sp = _a2sp(a)
echo $[type(sp)]

echo len: $[_opsp(sp, 'len')]

#echo $[len(sp)]

shopt -s ysh:upgrade

echo subst: @[_opsp(sp, 'subst')]
echo keys: @[_opsp(sp, 'keys')]

echo slice: @[_opsp(sp, 'slice', 2, 5)]

call _opsp(sp, 'set', 0, 'set0')

echo get0: $[_opsp(sp, 'get', 0)]
echo get1: $[_opsp(sp, 'get', 1)]
echo ---

to_append=(x y)
echo append
call _opsp(sp, 'append', to_append)
echo subst: @[_opsp(sp, 'subst')]
echo keys: @[_opsp(sp, 'keys')]
echo ---

echo unset
call _opsp(sp, 'unset', 11)
echo subst: @[_opsp(sp, 'subst')]
echo keys: @[_opsp(sp, 'keys')]

## STDOUT:
SparseArray
len: 6
subst: foo 25 26 27 bar sparse
keys: 0 1 2 3 4 10
slice: 26 27 bar
get0: set0
get1: 25
---
append
subst: set0 25 26 27 bar sparse x y
keys: 0 1 2 3 4 10 11 12
---
unset
subst: set0 25 26 27 bar sparse y
keys: 0 1 2 3 4 10 12
## END

## N-I bash/zsh/mksh/ash STDOUT:
## END


#### SparseArray: test length
case $SH in bash|zsh|mksh|ash) exit ;; esac

declare -a a=(x y z)

a[5]=z
var sp = _a2sp(a)

echo len=${#sp[@]}

a[10]=z
var sp = _a2sp(a)

echo len=${#sp[@]}


## STDOUT:
len=4
len=5
## END

## N-I bash/zsh/mksh/ash STDOUT:
## END


#### SparseArray: test "declare -p sp"
case $SH in zsh|ash) exit ;; esac

a0=()
a1=(1)
a2=(1 2)
a=(x y z w)
a[500]=100
a[1000]=100

case $SH in
bash|mksh)
  typeset -p a0 a1 a2 a
  exit ;;
esac

var a0 = _a2sp(a0)
var a1 = _a2sp(a1)
var a2 = _a2sp(a2)
var sp = _a2sp(a)
declare -p a0 a1 a2 sp

## STDOUT:
declare -a a0=()
declare -a a1=([0]=1)
declare -a a2=([0]=1 [1]=2)
declare -a sp=([0]=x [1]=y [2]=z [3]=w [500]=100 [1000]=100)
## END

## OK bash STDOUT:
declare -a a0=()
declare -a a1=([0]="1")
declare -a a2=([0]="1" [1]="2")
declare -a a=([0]="x" [1]="y" [2]="z" [3]="w" [500]="100" [1000]="100")
## END

## OK mksh STDOUT:
set -A a1
typeset a1[0]=1
set -A a2
typeset a2[0]=1
typeset a2[1]=2
set -A a
typeset a[0]=x
typeset a[1]=y
typeset a[2]=z
typeset a[3]=w
typeset a[500]=100
typeset a[1000]=100
## END

## N-I zsh/ash STDOUT:
## END

#### SparseArray: +=
case $SH in bash|zsh|mksh|ash) exit ;; esac

sp1[10]=a
sp1[20]=b
sp1[99]=c
var sp1 = _a2sp(sp1)
declare -p sp1
sp1+=(1 2 3)
declare -p sp1

## STDOUT:
declare -a sp1=([10]=a [20]=b [99]=c)
declare -a sp1=([10]=a [20]=b [99]=c [100]=1 [101]=2 [102]=3)
## END

## N-I bash/zsh/mksh/ash STDOUT:
## END


#### SparseArray: a[i]=v
case $SH in bash|zsh|mksh|ash) exit ;; esac

sp1[10]=a
sp1[20]=b
sp1[30]=c
var sp1 = _a2sp(sp1)
declare -p sp1
sp1[10]=X
sp1[25]=Y
sp1[90]=Z
declare -p sp1

## STDOUT:
declare -a sp1=([10]=a [20]=b [30]=c)
declare -a sp1=([10]=X [20]=b [25]=Y [30]=c [90]=Z)
## END

## N-I bash/zsh/mksh/ash STDOUT:
## END


#### SparseArray: Negative index with a[i]=v
case $SH in bash|zsh|mksh|ash) exit ;; esac

sp1[9]=x
var sp1 = _a2sp(sp1);

declare -p sp1
sp1[-1]=A
sp1[-4]=B
sp1[-8]=C
sp1[-10]=D
declare -p sp1

## STDOUT:
declare -a sp1=([9]=x)
declare -a sp1=([0]=D [2]=C [6]=B [9]=A)
## END

## N-I bash/zsh/mksh/ash STDOUT:
## END


#### SparseArray: Negative out-of-bound index with a[i]=v (1/2)
case $SH in bash|zsh|mksh|ash) exit ;; esac

sp1[9]=x
var sp1 = _a2sp(sp1);

sp1[-11]=E
declare -p sp1

## status: 1
## STDOUT:
## END
## STDERR:
  sp1[-11]=E
  ^~~~
[ stdin ]:6: fatal: Index -11 is out of bounds for array of length 10
## END

## N-I bash/zsh/mksh/ash status: 0
## N-I bash/zsh/mksh/ash STDERR:
## END


#### SparseArray: Negative out-of-bound index with a[i]=v (2/2)
case $SH in bash|zsh|mksh|ash) exit ;; esac

sp1[9]=x
var sp1 = _a2sp(sp1);

sp1[-21]=F
declare -p sp1

## status: 1
## STDOUT:
## END
## STDERR:
  sp1[-21]=F
  ^~~~
[ stdin ]:6: fatal: Index -21 is out of bounds for array of length 10
## END

## N-I bash/zsh/mksh/ash status: 0
## N-I bash/zsh/mksh/ash STDERR:
## END

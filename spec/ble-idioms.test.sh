## compare_shells: bash zsh mksh ash
## oils_failures_allowed: 2

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

# TODO: more InternalStringArray idioms / stress tests ?

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


#### shopt -u expand_aliases and eval
case $SH in zsh|mksh|ash) exit ;; esac

alias echo=false

function f {
  shopt -u expand_aliases
  eval -- "$1"
  shopt -s expand_aliases
}

f 'echo hello'

## STDOUT:
hello
## END
## N-I zsh/mksh/ash STDOUT:
## END


#### Tilde expansions in RHS of designated array initialization
case $SH in zsh|mksh|ash) exit ;; esac

HOME=/home/user
declare -A a
declare -A a=(['home']=~ ['hello']=~:~:~)
echo "${a['home']}"
echo "${a['hello']}"

## STDOUT:
/home/user
/home/user:/home/user:/home/user
## END

# Note: bash-5.2 has a bug that the tilde doesn't expand on the right hand side
# of [key]=value.  This problem doesn't happen in bash-3.1..5.1 and bash-5.3.
## BUG bash STDOUT:
~
~:~:~
## END

## N-I zsh/mksh/ash stdout-json: ""


#### InitializerList (BashArray): index increments with
case $SH in zsh|mksh|ash) exit 99;; esac
a=([100]=1 2 3 4)
printf 'keys: '; argv.py "${!a[@]}"
printf 'vals: '; argv.py "${a[@]}"
a=([100]=1 2 3 4 [5]=a b c d)
printf 'keys: '; argv.py "${!a[@]}"
printf 'vals: '; argv.py "${a[@]}"
## STDOUT:
keys: ['100', '101', '102', '103']
vals: ['1', '2', '3', '4']
keys: ['5', '6', '7', '8', '100', '101', '102', '103']
vals: ['a', 'b', 'c', 'd', '1', '2', '3', '4']
## END
## N-I zsh/mksh/ash status: 99
## N-I zsh/mksh/ash stdout-json: ""

#### InitializerList (BashArray): [k]=$v and [k]="$@"
case $SH in zsh|mksh|ash) exit 99;; esac
i=5
v='1 2 3'
a=($v [i]=$v)
printf 'keys: '; argv.py "${!a[@]}"
printf 'vals: '; argv.py "${a[@]}"

x=(3 5 7)
a=($v [i]="${x[*]}")
printf 'keys: '; argv.py "${!a[@]}"
printf 'vals: '; argv.py "${a[@]}"
a=($v [i]="${x[@]}")
printf 'keys: '; argv.py "${!a[@]}"
printf 'vals: '; argv.py "${a[@]}"
a=($v [i]=${x[*]})
printf 'keys: '; argv.py "${!a[@]}"
printf 'vals: '; argv.py "${a[@]}"
a=($v [i]=${x[@]})
printf 'keys: '; argv.py "${!a[@]}"
printf 'vals: '; argv.py "${a[@]}"
## STDOUT:
keys: ['0', '1', '2', '5']
vals: ['1', '2', '3', '1 2 3']
keys: ['0', '1', '2', '5']
vals: ['1', '2', '3', '3 5 7']
keys: ['0', '1', '2', '5']
vals: ['1', '2', '3', '3 5 7']
keys: ['0', '1', '2', '5']
vals: ['1', '2', '3', '3 5 7']
keys: ['0', '1', '2', '5']
vals: ['1', '2', '3', '3 5 7']
## END
## N-I zsh/mksh/ash status: 99
## N-I zsh/mksh/ash stdout-json: ""


#### InitializerList (BashAssoc): [k]=$v and [k]="$@"
case $SH in zsh|mksh|ash) exit 99;; esac
i=5
v='1 2 3'
declare -A a
a=([i]=$v)
printf 'keys: '; argv.py "${!a[@]}"
printf 'vals: '; argv.py "${a[@]}"

x=(3 5 7)
a=([i]="${x[*]}")
printf 'keys: '; argv.py "${!a[@]}"
printf 'vals: '; argv.py "${a[@]}"
a=([i]="${x[@]}")
printf 'keys: '; argv.py "${!a[@]}"
printf 'vals: '; argv.py "${a[@]}"
a=([i]=${x[*]})
printf 'keys: '; argv.py "${!a[@]}"
printf 'vals: '; argv.py "${a[@]}"
a=([i]=${x[@]})
printf 'keys: '; argv.py "${!a[@]}"
printf 'vals: '; argv.py "${a[@]}"
## STDOUT:
keys: ['i']
vals: ['1 2 3']
keys: ['i']
vals: ['3 5 7']
keys: ['i']
vals: ['3 5 7']
keys: ['i']
vals: ['3 5 7']
keys: ['i']
vals: ['3 5 7']
## END
## N-I zsh/mksh/ash status: 99
## N-I zsh/mksh/ash stdout-json: ""

#### InitializerList (BashArray): append to element
case $SH in zsh|mksh|ash) exit 99;; esac
hello=100
a=([hello]=1 [hello]+=2)
printf 'keys: '; argv.py "${!a[@]}"
printf 'vals: '; argv.py "${a[@]}"
a+=([hello]+=:34 [hello]+=:56)
printf 'keys: '; argv.py "${!a[@]}"
printf 'vals: '; argv.py "${a[@]}"
## STDOUT:
keys: ['100']
vals: ['12']
keys: ['100']
vals: ['12:34:56']
## END
## N-I zsh/mksh/ash status: 99
## N-I zsh/mksh/ash stdout-json: ""

#### InitializerList (BashAssoc): append to element
case $SH in zsh|mksh|ash) exit 99;; esac
declare -A a
hello=100
a=([hello]=1 [hello]+=2)
printf 'keys: '; argv.py "${!a[@]}"
printf 'vals: '; argv.py "${a[@]}"
a+=([hello]+=:34 [hello]+=:56)
printf 'keys: '; argv.py "${!a[@]}"
printf 'vals: '; argv.py "${a[@]}"
## STDOUT:
keys: ['hello']
vals: ['12']
keys: ['hello']
vals: ['12:34:56']
## END
# Bash >= 5.1 has a bug. Bash <= 5.0 is OK.
## BUG bash STDOUT:
keys: ['hello']
vals: ['2']
keys: ['hello']
vals: ['2:34:56']
## END
## N-I zsh/mksh/ash status: 99
## N-I zsh/mksh/ash stdout-json: ""

#### InitializerList (BashAssoc): non-index forms of element
case $SH in zsh|mksh|ash) exit 99;; esac
declare -A a
a=([j]=1 2 3 4)
echo "status=$?"
printf 'keys: '; argv.py "${!a[@]}"
printf 'vals: '; argv.py "${a[@]}"
## status: 1
## STDOUT:
## END
# Bash outputs warning messages and succeeds (exit status 0)
## BUG bash status: 0
## BUG bash STDOUT:
status=0
keys: ['j']
vals: ['1']
## END
## BUG bash STDERR:
bash: line 3: a: 2: must use subscript when assigning associative array
bash: line 3: a: 3: must use subscript when assigning associative array
bash: line 3: a: 4: must use subscript when assigning associative array
## END
## N-I zsh/mksh/ash status: 99
## N-I zsh/mksh/ash stdout-json: ""


#### InitializerList (BashArray): evaluation order (1)
# RHS of [k]=v are expanded when the initializer list is instanciated.  For the
# indexed array, the array indices are evaluated when the array is modified.
case $SH in zsh|mksh|ash) exit 99;; esac
i=1
a=([100+i++]=$((i++)) [200+i++]=$((i++)) [300+i++]=$((i++)))
printf 'keys: '; argv.py "${!a[@]}"
printf 'vals: '; argv.py "${a[@]}"
## STDOUT:
keys: ['104', '205', '306']
vals: ['1', '2', '3']
## END
## N-I zsh/mksh/ash status: 99
## N-I zsh/mksh/ash stdout-json: ""


#### InitializerList (BashArray): evaluation order (2)
# When evaluating the index, the modification to the array by the previous item
# of the initializer list is visible to the current item.
case $SH in zsh|mksh|ash) exit 99;; esac
a=([0]=1+2+3 [a[0]]=10 [a[6]]=hello)
printf 'keys: '; argv.py "${!a[@]}"
printf 'vals: '; argv.py "${a[@]}"
## STDOUT:
keys: ['0', '6', '10']
vals: ['1+2+3', '10', 'hello']
## END
## N-I zsh/mksh/ash status: 99
## N-I zsh/mksh/ash stdout-json: ""


#### InitializerList (BashArray): evaluation order (3)
# RHS should be expanded before any modification to the array.
case $SH in zsh|mksh|ash) exit 99;; esac
a=(old1 old2 old3)
a=("${a[2]}" "${a[0]}" "${a[1]}" "${a[2]}" "${a[0]}")
printf 'keys: '; argv.py "${!a[@]}"
printf 'vals: '; argv.py "${a[@]}"
a=(old1 old2 old3)
old1=101 old2=102 old3=103
new1=201 new2=202 new3=203
a+=([0]=new1 [1]=new2 [2]=new3 [5]="${a[2]}" [a[0]]="${a[0]}" [a[1]]="${a[1]}")
printf 'keys: '; argv.py "${!a[@]}"
printf 'vals: '; argv.py "${a[@]}"
## STDOUT:
keys: ['0', '1', '2', '3', '4']
vals: ['old3', 'old1', 'old2', 'old3', 'old1']
keys: ['0', '1', '2', '5', '201', '202']
vals: ['new1', 'new2', 'new3', 'old3', 'old1', 'old2']
## END
## N-I zsh/mksh/ash status: 99
## N-I zsh/mksh/ash stdout-json: ""


#### Issue #1069 [57] - Variable v should be visible after IFS= eval 'local v=...'

set -u

f() {
  # The temp env messes it up
  IFS= eval "local v=\"\$*\""

  # Bug does not appear with only eval
  # eval "local v=\"\$*\""

  #declare -p v
  echo v=$v

  # test -v v; echo "v defined $?"
}

f h e l l o

## STDOUT:
v=hello
## END


#### Issue #1069 [59] - Assigning Str to BashArray/BashAssoc should not remove BashArray/BashAssoc
case $SH in zsh|ash) exit ;; esac

a=(1 2 3)
a=99
typeset -p a

typeset -A A=([k]=v)
A=99
typeset -p A

## STDOUT:
declare -a a=([0]="99" [1]="2" [2]="3")
declare -A A=([0]="99" [k]="v" )
## END

## OK mksh status: 1
## OK mksh STDOUT:
set -A a
typeset a[0]=99
typeset a[1]=2
typeset a[2]=3
## END

## N-I zsh/ash STDOUT:
## END

#### Issue #1069 [53] - LHS array parsing a[1 + 2]=3, etc.
case $SH in zsh|mksh|ash) exit ;; esac

a[1 + 2]=7
a[3|4]=8
a[(1+2)*3]=9

declare -p a

## STDOUT:
declare -a a=([3]="7" [7]="8" [9]="9")
## END

## N-I zsh/mksh/ash STDOUT:
## END

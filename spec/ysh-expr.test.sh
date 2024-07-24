
#### command sub $(echo hi)
var x = $(echo hi)
var y = $(echo '')
# Make sure we can operate on these values
echo x=${x:-default} y=${y:-default}
## STDOUT:
x=hi y=default
## END

#### shell array %(a 'b c')
shopt -s parse_at
var x = %(a 'b c')
var empty = %()
argv.py / @x @empty /

## STDOUT:
['/', 'a', 'b c', '/']
## END

#### empty array and simple_word_eval (regression test)
shopt -s parse_at simple_word_eval
var empty = :| |
echo len=$[len(empty)]
argv.py / @empty /

## STDOUT:
len=0
['/', '/']
## END

#### Empty array and assignment builtin (regression)
# Bug happens with shell arrays too
empty=()
declare z=1 "${empty[@]}"
echo z=$z
## STDOUT:
z=1
## END

#### Shell arrays support tilde detection, static globbing, brace detection
shopt -s parse_at simple_word_eval
touch {foo,bar}.py
HOME=/home/bob
no_dynamic_glob='*.py'

var x = %(~/src *.py {andy,bob}@example.com $no_dynamic_glob)
argv.py @x
## STDOUT:
['/home/bob/src', 'bar.py', 'foo.py', 'andy@example.com', 'bob@example.com', '*.py']
## END

#### Set $HOME using 'var' (i.e. Oil string var in word evaluator)
var HOME = "foo"
echo $HOME
echo ~
## STDOUT:
foo
foo
## END

#### Use shell var in Oil expression
x='abc'
var length = len(x)  # length in BYTES, unlike ${#x}
echo $length
## STDOUT:
3
## END

#### Length doesn't apply to BashArray
x=(a b c)
x[10]=A
x[20]=B

# shell style: length is 5
echo shell=${#x[@]}

# Length could be 20, but we may change the representation to Dict[int, str]
echo ysh=$[len(x)]

## status: 3
## STDOUT:
shell=5
## END

#### $[len(x)] inside strings
var s = "abc"
echo -$[len(s)]-

# This already has a meaning ...
#echo "-$len(x)-"
#echo "-${len}(x)-"

## STDOUT:
-3-
## END

#### Func with multiple args in multiple contexts
shopt --set ysh:upgrade  # needed for math.ysh

source $LIB_YSH/math.ysh

var x = max(1+2, 3+4)
echo $x $[max(1+2, 3+4)]

## STDOUT:
7 7
## END


#### Trailing Comma in Param list
shopt --set ysh:upgrade  # needed for math.ysh

source $LIB_YSH/math.ysh

var x = max(1+2, 3+4,)
echo $x $[max(1+2, 3+4,)]

## STDOUT:
7 7
## END

#### nested expr contexts
var s = "123"

# lex_mode_e.ShCommand -> Expr -> ShCommand -> Expr
var x = $(echo $'len\n' $[len(s)])
echo $x
## STDOUT:
len 3
## END


# TODO:
# - test keyword args
# - test splatting *args, **kwargs
# - Multiline parsing
#
# var x = max(
#   1+2,
#   3+4,
# )
# echo $x $max(
#   1+2,
#   3+4,
# )

#### YSH var used with shell arithmetic
var w = "3"
echo lt=$(( w < 4 ))
echo gt=$(( w > 4 ))

var z = 3
echo lt=$(( z < 4 ))
echo gt=$(( z > 4 ))
## STDOUT:
lt=1
gt=0
lt=1
gt=0
## END

#### Parse { var x = 42 }
shopt -s oil:upgrade
g() { var x = 42 }

var x = 1
f() { var x = 42; setvar x = 43 }
f
echo x=$x
## STDOUT:
x=1
## END

#### double quoted
var foo = "bar"
var x = "-$foo-${foo}-${undef:-default}-"
echo $x
## STDOUT:
-bar-bar-default-
## END

#### double quoted respects strict_array
shopt -s strict:all
declare -a a=(one two three)
var x = "-${a[@]}-"
echo $x
## status: 1
## stdout-json: ""

#### simple var sub $name $0 $1 $? etc.
( exit 42 )
var status = $?
echo status=$status

set -- a b c
var one = $1
var two = $2
echo $one $two

var named = "$one"  # equivalent to 'one'
echo named=$named

## STDOUT:
status=42
a b
named=a
## END

#### braced var sub ${x:-default}

# without double quotes

var b = ${foo:-default}
echo $b
var c = ${bar:-"-$b-"}
echo $c

var d = "${bar:-"-$c-"}"  # another one
echo $d

## STDOUT:
default
-default-
--default--
## END

#### braced var sub respects strict_array
set -- a b c
var x = ${undef:-"$@"}
echo $x
shopt -s strict_array
setvar x = ${undef:-"$@"}
echo $x
## status: 1
## STDOUT:
a b c
## END


#### null / true / false
shopt -s oil:upgrade
var n = null
if (n) {
  echo yes
} else {
  echo no
}
var t = true
if (t) {
  echo yes
} else {
  echo no
}
var f = false
if (f) {
  echo yes
} else {
  echo no
}
## STDOUT:
no
yes
no
## END

#### Integer literals
var d = 123
var b = 0b11
var o = 0o123
var h = 0xff
echo $d $b $o $h
## STDOUT:
123 3 83 255
## END

#### Integer literals with underscores
const dec = 65_536
const bin = 0b0001_0101
const oct = 0o001_755
const hex = 0x0001_000f

echo SHELL
echo $dec
echo $bin
echo $oct
echo $hex
const x = 1_1 + 0b1_1 + 0o1_1 + 0x1_1
echo sum $x

# This works under Python 3.6, but the continuous build has earlier versions
if false; then
  echo ---
  echo PYTHON

  python3 -c '
  print(65_536)
  print(0b0001_0101)
  print(0o001_755)
  print(0x0001_000f)

  # Weird syntax
  print("sum", 1_1 + 0b1_1 + 0o1_1 + 0x1_1)
  '
fi

## STDOUT:
SHELL
65536
21
1005
65551
sum 40
## END

#### Backslash char literal (is an integer)
const newline = \n
const backslash = \\
const sq = \'
const dq = \"
echo "$newline $backslash $sq $dq"
## STDOUT:
10 92 39 34
## END

#### \u{3bc} is char literal
shopt -s oil:all

var mu = \u{3bc}
if (mu === 0x3bc) {  # this is the same!
  echo 'yes'
}
echo "mu $mu"
## STDOUT:
yes
mu 956
## END

#### Exponentiation with **
var x = 2**3
echo $x

var y = 2.0 ** 3.0  # NOT SUPPORTED
echo 'should not get here'

## status: 3
## STDOUT:
8
## END

#### Float Division
pp line (5/2)
pp line (-5/2)
pp line (5/-2)
pp line (-5/-2)

echo ---

var x = 9
setvar x /= 2
pp line (x)

var x = -9
setvar x /= 2
pp line (x)

var x = 9
setvar x /= -2
pp line (x)

var x = -9
setvar x /= -2
pp line (x)


## STDOUT:
(Float)   2.5
(Float)   -2.5
(Float)   -2.5
(Float)   2.5
---
(Float)   4.5
(Float)   -4.5
(Float)   -4.5
(Float)   4.5
## END

#### Integer Division (rounds toward zero)
pp line (5//2)
pp line (-5//2)
pp line (5//-2)
pp line (-5//-2)

echo ---

var x = 9
setvar x //= 2
pp line (x)

var x = -9
setvar x //= 2
pp line (x)

var x = 9
setvar x //= -2
pp line (x)

var x = -9
setvar x //= -2
pp line (x)

## STDOUT:
(Int)   2
(Int)   -2
(Int)   -2
(Int)   2
---
(Int)   4
(Int)   -4
(Int)   -4
(Int)   4
## END

#### % operator is remainder
pp line ( 5 % 3)
pp line (-5 % 3)

# negative divisor illegal (tested in test/ysh-runtime-errors.sh)
#pp line ( 5 % -3)
#pp line (-5 % -3)

var z = 10
setvar z %= 3
pp line (z)

var z = -10
setvar z %= 3
pp line (z)

## STDOUT:
(Int)   2
(Int)   -2
(Int)   1
(Int)   -1
## END

#### Bitwise logical
var a = 0b0101 & 0b0011
echo $a
var b = 0b0101 | 0b0011
echo $b
var c = 0b0101 ^ 0b0011
echo $c
var d = ~b
echo $d
## STDOUT:
1
7
6
-8
## END

#### Shift operators
var a = 1 << 4
echo $a
var b = 16 >> 4
echo $b
## STDOUT:
16
1
## END

#### multiline strings, list, tuple syntax for list, etc.
var dq = "
dq
2
"
echo dq=$[len(dq)]

var sq = '
sq
2
'
echo sq=$[len(sq)]

var mylist = [
  1,
  2,
  3,
]
echo mylist=$[len(mylist)]

var mytuple = (1,
  2, 3)
echo mytuple=$[len(mytuple)]

## STDOUT:
dq=6
sq=6
mylist=3
mytuple=3
## END

#### multiline dict

# Note: a pair has to be all on one line.  We could relax that but there isn't
# a strong reason to now.

var mydict = { a:1,
  b: 2,
}
echo mydict=$[len(mydict)]
## STDOUT:
mydict=2
## END

#### multiline array and command sub (only here docs disallowed)
var array = %(
  one
  two
  three
)
echo array=$[len(array)]

var comsub = $(
echo hi
echo bye
)
echo comsub=$[len(comsub)]

## STDOUT:
array=3
comsub=6
## END

#### obj->method()
var s = 'hi'

# TODO: This does a bound method thing we probably don't want
var s2 = s=>upper()
echo $s2
## STDOUT:
HI
## END

#### obj->method does NOT give you a bound method
var s = 'hi'
var method = s->upper
echo $method
## status: 3
## stdout-json: ""

#### d.key
var d = {name: 'andy'}
var x = d.name
echo $x
## STDOUT:
andy
## END

#### a ++ b for string/list concatenation
shopt -s parse_brace

var i = 'abc'
var j = 'de'
var k = i ++ j
echo string $k


var a = [1, 2]
var b = [3]
var c = a ++ b
echo list len=$[len(c)]

echo ---

try {
  = 'ab' ++ 3
}
echo Str Int $_status

try {
  = [1, 2] ++ 3
}
echo List Int $_status

try {
  = 3 ++ 'ab'
}
echo Int Str $_status

## STDOUT:
string abcde
list len=3
---
Str Int 3
List Int 3
Int Str 3
## END

#### s ~~ glob and s !~~ glob
shopt -s oil:all

if ('foo.py' ~~ '*.py') {
  echo yes
}
if ('foo.py' !~~ '*.sh') {
  echo no
}
## STDOUT:
yes
no
## END

#### Type Errors
shopt --set parse_brace

# TODO: It might be nice to get a message
try {
  var x = {} + []
}
echo $_status

try {
  setvar x = {} + 3
}
echo $_status

try {
  = 'foo' ++ 3
}
echo $_status

try {
  = 'foo' ++ 3
}
echo $_status

## STDOUT:
3
3
3
3
## END


#### can't use ++ on integers
var x = 12 ++ 3
echo $x
## status: 3
## STDOUT:
## END

#### can't do mystr ++ mylist
= ["s"] + "t"
## status: 3
## STDOUT:
## END


#### expression literals
var e = ^[1 + 2]

echo type=$[type(e)]
echo $[evalExpr(e)]

var e = ^[2 < 1]
echo $[evalExpr(e)]

var x = 42
var e = ^[42 === x and true]
echo $[evalExpr(e)]

var mylist = ^[3, 4]
pp line (evalExpr(mylist))

## STDOUT:
type=Expr
3
false
true
(List)   [3,4]
## END

#### No list comprehension in ^[]

var mylist = ^[x for x in y]  
pp line (evalExpr(mylist))

## status: 2
## STDOUT:
## END


#### expression literals, evaluation failure
var e = ^[1 / 0]
call evalExpr(e)
## status: 3
## STDOUT:
## END

#### expression literals, lazy evaluation
var x = 0
var e = ^[x]

setvar x = 1
echo result=$[evalExpr(e)]
## STDOUT:
result=1
## END

#### expression literals, sugar for strings
var x = 0
var e = ^"x is $x"

setvar x = 1
echo result=$[evalExpr(e)]
## STDOUT:
result=x is 1
## END

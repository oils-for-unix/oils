# Test Oil expressions

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

#### Length in two different contexts
x=(a b c)
x[10]=A
x[20]=B

# shell style: length is 5
echo shell=${#x[@]}

# Oil function call: length is 20.  I think that makes sense?  It's just a
# different notion of length.
echo oil=$[len(x)]

## STDOUT:
shell=5
oil=21
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
var x = max(1+2, 3+4)
echo $x $[max(1+2, 3+4)]

## STDOUT:
7 7
## END


#### Trailing Comma in Param list
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

#### Test value.Obj inside shell arithmetic
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

#### Pound char literal (is an integer)
const a  = #'a'
const A = #'A'
echo "$a $A"
## STDOUT:
97 65
## END

#### The literal #''' isn't accepted (use \' instead)

# This looks too much like triple quoted strings!

echo nope
const bad = #'''
echo "$bad"

## status: 2
## STDOUT:
nope
## END

#### Float Literals
shopt -s oil:upgrade
# 1+2 2.3
var x = 1.2 + 23.0e-1  # 3.5
if (x < 3.9) {
  echo less
}
if (x > 3.4) {
  echo great
}
## STDOUT:
less
great
## END

#### Float Literals with _ (requires re2c refinement)
shopt -s oil:upgrade
# 1+2 + 2.3
# add this _ here
var x = 1.2 + 2_3.0e-1  # 3.5
if (x < 3.9) {
  echo less
}
if (x > 3.4) {
  echo great
}
## STDOUT:
less
great
## END

#### "in" and "not in" on Dicts

var d = {spam: 42, eggs: []}

var b = 'spam' in d
echo $b

var b = 'zz' in d
echo $b

var b = 'zz' not in d
echo $b

var L = [1, 2, 3]
var b = 3 in L  # not allowed!

echo should not get here

## status: 3
## STDOUT:
true
false
true
## END

#### dict with 'bare word' keys
var d0 = {}
echo len=$[len(d0)]
var d1 = {name: "hello"}
echo len=$[len(d1)]
var d2 = {name: "hello", other: 2}
echo len=$[len(d2)]
## STDOUT:
len=0
len=1
len=2
## END

#### dict with expression keys
var d1 = {['name']: "hello"}
echo len=$[len(d1)]
var v = d1['name']
echo $v

var key='k'
var d2 = {["$key"]: "bar"}
echo len=$[len(d2)]
var v2 = d2['k']
echo $v2

## STDOUT:
len=1
hello
len=1
bar
## END


#### dict literal with implicit value
var name = 'foo'
var d1 = {name}
echo len=$[len(d1)]
var v1 = d1['name']
echo $v1

var d2 = {name, other: 'val'}
echo len=$[len(d2)]
var v2 = d2['name']
echo $v2

## STDOUT:
len=1
foo
len=2
foo
## END

#### Dict literal with string keys
var d = {'sq': 123}
var v = d['sq']
echo $v

var x = "q"
var d2 = {"d$x": 456}
var v2 = d2["dq"]
echo $v2
## STDOUT:
123
456
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

#### Exponentiation with **
var x = 2**3
echo $x

var y = 2.0 ** 3.0  # NOT SUPPORTED
echo 'should not get here'

## status: 3
## STDOUT:
8
## END

#### Two Kinds of Division
var x = 5/2
echo $x
var y = 5 // 2
echo $y
## STDOUT:
2.5
2
## END

#### mod operator
= 5 % 3
= -5 % 3
## STDOUT:
(Int)   2
(Int)   1
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
var s2 = s->upper()
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
var i = 'abc'
var j = 'de'
var k = i ++ j
echo $k

var a = [1, 2]
var b = [3]
var c = a ++ b
echo len=$[len(c)]

## STDOUT:
abcde
len=3
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
  _ 'foo' ++ 3
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




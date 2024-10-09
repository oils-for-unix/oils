# spec/ysh-stdlib

## our_shell: ysh

#### any
source $LIB_YSH/list.ysh

json write (any([]))
json write (any([true]))
json write (any([false]))
json write (any([true, false]))
json write (any([false, true]))
json write (any([false, false]))
json write (any([false, true, false]))
json write (any([false, false, null, ""]))  # null and "" are falsey
json write (any(["foo"]))  # "foo" is truthy
## STDOUT:
false
true
false
true
true
false
true
false
true
## END

#### all
source $LIB_YSH/list.ysh

json write (all([]))
json write (all([true]))
json write (all([false]))
json write (all([true, true]))
json write (all([true, false]))
json write (all([false, true]))
json write (all([false, false]))
json write (all([false, true, false]))
json write (all(["foo"]))
json write (all([""]))
## STDOUT:
true
true
false
true
false
false
false
false
true
false
## END

#### more any() and all()
source $LIB_YSH/list.ysh

var a1 = all( :|yes yes| )
var a2 = all( :|yes ''| )
var a3 = all( :|'' ''| )
# This should be true and false or what?
write $a1 $a2 $a3
write __

var x1 = any( :|yes yes| )
var x2 = any( :|yes ''| )
var x3 = any( :|'' ''| )
write $x1 $x2 $x3

## STDOUT:
true
false
false
__
true
true
false
## END

#### sum
source $LIB_YSH/list.ysh

json write (sum([]))
json write (sum([0]))
json write (sum([1, 2, 3]))

var start = 42

echo

write $[sum( 0 .. 3 )]
write $[sum( 0 .. 3; start=42)]
write $[sum( 0 .. 0, start=42)]

## STDOUT:
0
0
6

3
45
42
## END

#### repeat() string

source $LIB_YSH/list.ysh

echo three=$[repeat('foo', 3)]
echo zero=$[repeat('foo', 0)]
echo negative=$[repeat('foo', -1)]

## STDOUT:
three=foofoofoo
zero=
negative=
## END

#### repeat() list

source $LIB_YSH/list.ysh

var L = ['foo', 'bar']
echo three @[repeat(L, 3)]
echo zero @[repeat(L, 0)]
echo negative @[repeat(L, -1)]

## STDOUT:
three foo bar foo bar foo bar
zero
negative
## END

#### repeat() error

try {
  $SH -c '
  source $LIB_YSH/list.ysh
  pp test_ (repeat(null, 3))
  echo bad'
}
echo code=$[_error.code]

try {
  $SH -c '
  source $LIB_YSH/list.ysh
  pp test_ (repeat({}, 3))
  echo bad'
}
echo code=$[_error.code]

try {
  $SH -c '
  source $LIB_YSH/list.ysh
  pp test_ (repeat(42, 3))
  echo bad'
}
echo code=$[_error.code]

## STDOUT:
code=10
code=10
code=10
## END


#### smoke test for two.sh

source --builtin osh/two.sh

log 'hi'

set +o errexit
( die "bad" )
echo status=$?

## STDOUT:
status=1
## END

#### smoke test for stream.ysh and table.ysh 

shopt --set redefine_proc_func   # byo-maybe-main

source $LIB_YSH/stream.ysh
source $LIB_YSH/table.ysh

## status: 0


# spec/ysh-stdlib

## our_shell: ysh

#### identity
source --builtin funcs.ysh

for x in (['a', 1, null, { foo: 'bar' }, [40, 2]]) {
  json write (identity(x))
}

## STDOUT:
"a"
1
null
{
  "foo": "bar"
}
[
  40,
  2
]
## END

#### max
source --builtin math.ysh

json write (max(1, 2))
json write (max([1, 2, 3]))

try { call max([]) }
echo status=$_status

try { call max(1, 2) }
echo status=$_status

try { call max(1, 2, 3) }
echo status=$_status

try { call max() }
echo status=$_status

## STDOUT:
2
3
status=3
status=0
status=3
status=3
## END

#### min
source --builtin math.ysh

json write (min(2, 3))
json write (min([1, 2, 3]))

try { call min([]) }
echo status=$_status

try { call min(2, 3) }
echo status=$_status

try { call min(1, 2, 3) }
echo status=$_status

try { call min() }
echo status=$_status

## STDOUT:
2
1
status=3
status=0
status=3
status=3
## END

#### abs
source --builtin math.ysh

json write (abs(-1))
json write (abs(0))
json write (abs(1))
json write (abs(42))
json write (abs(-42))

try { call abs(-42) }
echo status=$_status

## STDOUT:
1
0
1
42
42
status=0
## END

#### any
source --builtin list.ysh

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
source --builtin list.ysh

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

#### sum
source --builtin list.ysh

json write (sum([]))
json write (sum([0]))
json write (sum([1, 2, 3]))
## STDOUT:
0
0
6
## END


#### repeat() string

source --builtin list.ysh

echo three=$[repeat('foo', 3)]
echo zero=$[repeat('foo', 0)]
echo negative=$[repeat('foo', -1)]

## STDOUT:
three=foofoofoo
zero=
negative=
## END

#### repeat() list

source --builtin list.ysh

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
  source --builtin list.ysh
  pp line (repeat(null, 3))
  echo bad'
}
echo code=$[_error.code]

try {
  $SH -c '
  source --builtin list.ysh
  pp line (repeat({}, 3))
  echo bad'
}
echo code=$[_error.code]

try {
  $SH -c '
  source --builtin list.ysh
  pp line (repeat(42, 3))
  echo bad'
}
echo code=$[_error.code]

## STDOUT:
code=10
code=10
code=10
## END

# spec/ysh-stdlib

## our_shell: ysh
## oils_failures_allowed: 0

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

try { _ max([]) }
echo status=$_status

try { _ max(1, 2) }
echo status=$_status

try { _ max(1, 2, 3) }
echo status=$_status

try { _ max() }
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

try { _ min([]) }
echo status=$_status

try { _ min(2, 3) }
echo status=$_status

try { _ min(1, 2, 3) }
echo status=$_status

try { _ min() }
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

try { _ abs(-42) }
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

#### reversed
source --builtin list.ysh

json write (reversed([]))
json write (reversed([0]))
json write (reversed([2, 1, 3]))
json write (reversed(["hello", "world"]))

var immutable = [1, 2, 3]
_ reversed(immutable)
json write (immutable)
## STDOUT:
[

]
[
  0
]
[
  3,
  1,
  2
]
[
  "world",
  "hello"
]
[
  1,
  2,
  3
]
## END

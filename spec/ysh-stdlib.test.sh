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
status=1
status=1
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
status=1
status=1
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

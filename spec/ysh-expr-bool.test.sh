#### or short circuits
shopt -s ysh:upgrade

var x = [1, 2]
if (true or x[3]) {
  echo OK
}
## STDOUT:
OK
## END

#### and short circuits
shopt -s ysh:upgrade

var x = [1, 2]
if (false and x[3]) {
  echo bad
} else {
  echo OK
}

## STDOUT:
OK
## END

#### not operator behaves like Python

# consistent with if statement, ternary if, and, or

pp line (not "s")
pp line (not 3)
pp line (not 4.5)
pp line (not {})
pp line (not [])
pp line (not false)
pp line (not true)

## STDOUT:
(Bool)   false
(Bool)   false
(Bool)   false
(Bool)   true
(Bool)   true
(Bool)   true
(Bool)   false
## END

#### not, and, or

var a = not true
echo $a
var b = true and false
echo $b
var c = true or false
echo $c

## STDOUT:
false
false
true
## END


#### and-or chains for typed data

python2 -c 'print(None or "s")'
python2 -c 'print(None and "s")'

python2 -c 'print("x" or "y")'
python2 -c 'print("x" and "y")'

python2 -c 'print("" or "y")'
python2 -c 'print("" and "y")'

python2 -c 'print(42 or 0)'
python2 -c 'print(42 and 0)'

python2 -c 'print(0 or 42)'
python2 -c 'print(0 and 42)'

python2 -c 'print(0.0 or 0.5)'
python2 -c 'print(0.0 and 0.5)'

python2 -c 'print(["a"] or [])'
python2 -c 'print(["a"] and [])'

python2 -c 'print({"d": 1} or {})'
python2 -c 'print({"d": 1} and {})'

python2 -c 'print(0 or 0.0 or False or [] or {} or "OR")'
python2 -c 'print(1 and 1.0 and True and [5] and {"d":1} and "AND")'

echo ---

json write (null or "s")
json write (null and "s")

echo $["x" or "y"]
echo $["x" and "y"]

echo $["" or "y"]
echo $["" and "y"]

echo $[42 or 0]
echo $[42 and 0]

echo $[0 or 42]
echo $[0 and 42]

echo $[0.0 or 0.5]
echo $[0.0 and 0.5]

pp line (["a"] or [])
pp line (["a"] and [])

pp line ({"d": 1} or {})
pp line ({"d": 1} and {})

echo $[0 or 0.0 or false or [] or {} or "OR"]
echo $[1 and 1.0 and true and [5] and {"d":1} and "AND"]

declare -a array=(1 2 3)
pp line (array or 'yy')

declare -A assoc=([k]=v)
pp line (assoc or 'zz')

## STDOUT:
s
None
x
y
y

42
0
42
0
0.5
0.0
['a']
[]
{'d': 1}
{}
OR
AND
---
"s"
null
x
y
y

42
0
42
0
0.5
0.0
(List)   ["a"]
(List)   []
(Dict)   {"d":1}
(Dict)   {}
OR
AND
(BashArray)   ["1","2","3"]
(BashAssoc)   {"k":"v"}
## END

#### x if b else y
var b = true
var i = 42
var t = i+1 if b else i-1
echo $t
var f = i+1 if false else i-1
echo $f
## STDOUT:
43
41
## END


#### not operator behaves like Python

# consistent with if statement, ternary if, and, or

= not "s"
= not 3
= not 4.5
= not {}
= not []
= not false
= not true

## STDOUT:
(Bool)   False
(Bool)   False
(Bool)   False
(Bool)   True
(Bool)   True
(Bool)   True
(Bool)   False
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

json write --pretty=false (["a"] or [])
json write --pretty=false (["a"] and [])

json write --pretty=false ({"d": 1} or {})
json write --pretty=false ({"d": 1} and {})

echo $[0 or 0.0 or false or [] or {} or "OR"]
echo $[1 and 1.0 and true and [5] and {"d":1} and "AND"]

declare -a array=(1 2 3)
json write --pretty=false (array or 'yy')

declare -A assoc=([k]=v)
json write --pretty=false (assoc or 'zz')

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
["a"]
[]
{"d":1}
{}
OR
AND
["1","2","3"]
{"k":"v"}
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


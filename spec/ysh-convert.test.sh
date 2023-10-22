

#### bool() conversion
echo "$[bool(1234)]"
echo "$[bool(0)]"
echo "$[bool('foo')]"
echo "$[bool(true)]"
echo "$[bool(1.234)]"
echo "$[bool([])]"
echo "$[bool({})]"
echo "$[bool(null)]"
echo "$[bool(len)]"
echo "$[bool('foo'->startswith)]"
echo "$[bool(1..3)]"
## STDOUT:
true
false
true
true
true
false
false
false
true
true
true
## END

#### bool() more
var a = bool( :|| )
var b = bool( :|foo| )
write $a $b
## STDOUT:
false
true
## END


#### int() conversion
echo "$[int(1234)]"
echo "$[int('1234')]"
echo "$[int(1.234)]"
## STDOUT:
1234
1234
1
## END

#### int() more
var a = int("3")
var b = int("-35")
write $a $b

var c = int("bad")
echo 'should not get here'

## status: 3
## STDOUT:
3
-35
## END

#### float() conversion
echo "$[float(1234)]"
echo "$[float('1.234')]"
echo "$[float(2.345)]"
## STDOUT:
1234.0
1.234
2.345
## END

#### float() overflow / underflow

var a = float("1.2")
var b = float("3.4")

var c = float("42.1e500")
var d = float("-42.1e500")

write $a $b $c $d
## STDOUT:
1.2
3.4
inf
-inf
## END

#### str() conversion
echo "$[str(1234)]"
echo "$[str(1.234)]"
echo "$[str('foo')]"
## STDOUT:
1234
1.234
foo
## END

#### dict() converts from BashAssoc to Dict
declare -A foo
foo=([a]=1 [b]=2 [c]=3)

json write (type(foo))
json write (dict(foo))
## STDOUT:
"BashAssoc"
{
  "a": "1",
  "b": "2",
  "c": "3"
}
## END

#### dict() does shallow copy
var d = {'a': 1}
var d2 = d
setvar d2['b'] = 2
echo $['b' in d] # d2 should be an alias for d

var d3 = dict(d)
setvar d3['c'] = 3

# d3 should NOT be an alias
echo $['c' in d]
echo $['c' in d3]
## STDOUT:
true
false
true
## END

#### list() does shallow copy
var l = [1]
var l2 = l
:: l2->append(2)
echo $[len(l)] # d2 should be an alias for d

var l3 = list(l)
_ l3->append(3)

# l3 should NOT be an alias
echo $[len(l)]
echo $[len(l3)]
## STDOUT:
2
2
3
## END

#### list() from Dict
shopt -s ysh:upgrade

var a = list({'a': 1, 'foo': 'bar'})
write @a
## STDOUT:
a
foo
## END


#### list() from range
shopt -s ysh:upgrade

var mylist = list(0..3)
write @mylist
## STDOUT:
0
1
2
## END


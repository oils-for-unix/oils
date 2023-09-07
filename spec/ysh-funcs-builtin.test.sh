## our_shell: ysh
## oils_failures_allowed: 1

#### join()
var x = :|a b 'c d'|

var y = join(x)
argv.py $y

var z = join(x, ":")
argv.py $z
## STDOUT:
['abc d']
['a:b:c d']
## END

#### abs

source --builtin math.ysh

# Also test smooshing
write $[abs(-5)]$[abs(-0)]$[abs(5)]
write $[abs(-5)] $[abs(-0)] $[abs(5)]
## STDOUT:
505
5
0
5
## END

#### any() and all()
source --builtin list.ysh

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

#### sum()
source --builtin list.ysh

var start = 42

write $[sum( 0:3 )]
write $[sum( 0:3, start)]
write $[sum( 0:0, start)]
## STDOUT:
3
45
42
## END

#### List->reverse()
var x = list(0:3)
_ x->reverse()
write @x
## STDOUT:
2
1
0
## END

#### @[split(x)] respects IFS
setvar IFS = ":"
var x = "one:two:three"
argv.py @[split(x)]
## STDOUT:
['one', 'two', 'three']
## END

#### @[maybe(x)]
setvar empty = ''
setvar x = 'X'
argv.py a @[maybe(empty)] @[maybe(x)] b

setvar n = null
argv.py a @[maybe(n)] b

## STDOUT:
['a', 'X', 'b']
['a', 'b']
## END

#### maybe() on invalid type is fatal error

# not allowed
setvar marray = :||
argv.py a @[maybe(marray)] b
echo done
## status: 3
## STDOUT:
## END

#### split() on invalid type is fatal error
var myarray = :| --all --long |
write -- @[myarray]
write -- @[split(myarray)]
## status: 3
## STDOUT:
--all
--long
## END

#### @[glob(x)]

# empty glob
write -- A @[glob('__nope__')] B
echo ___

touch -- a.z b.z -.z
write -- @[glob('?.z')]
echo ___

# add it back
shopt -s dashglob
write -- @[glob('?.z')]

## STDOUT:
A
B
___
a.z
b.z
___
-.z
a.z
b.z
## END


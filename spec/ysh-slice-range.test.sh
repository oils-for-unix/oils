# Test a[1]

#### precedence of 1:3 vs comparison

# This test exposed nondeterminism in CPython itself!  Gah.  Is this because of
# the hashing?
# Python xrange objects probably shouldn't even be comparable!
#
# = 1:3 < 1:4
# >>> xrange(1,3)  < xrange(1,4)
# False
# >>> xrange(1,3)  < xrange(1,4)
# True

= 1:3

## STDOUT:
(xrange)   xrange(1, 3)
## END

#### precedence of 1:3 vs bitwise operator
= 3:3|4
## STDOUT:
(xrange)   xrange(3, 7)
## END

#### subscript and slice :| 1 2 3 4 |
var myarray = :|1 2 3 4|
= myarray[1]
= myarray[1:3]

echo 'implicit'
= myarray[:2]
= myarray[2:]

echo 'out of bounds'
= myarray[:5]
= myarray[-5:]

# Stride not supported
#= myarray[1:4:2]

# Now try omitting some
#= myarray[1:4:2]
## STDOUT:
(Str)   '2'
(List)   ['2', '3']
implicit
(List)   ['1', '2']
(List)   ['3', '4']
out of bounds
(List)   ['1', '2', '3', '4']
(List)   ['1', '2', '3', '4']
## END

#### subscript and slice of List
var mylist = [1,2,3,4]
= mylist[1]
= mylist[1:3]

echo 'implicit'
= mylist[:2]
= mylist[2:]
## STDOUT:
(Int)   2
(List)   [2, 3]
implicit
(List)   [1, 2]
(List)   [3, 4]
## END

#### expressions and negative indices
var myarray = %(1 2 3 4 5)
= myarray[-1]
= myarray[-4:-2]

echo 'implicit'
= myarray[:-2]
= myarray[-2:]
## STDOUT:
(Str)   '5'
(List)   ['2', '3']
implicit
(List)   ['1', '2', '3']
(List)   ['4', '5']
## END

#### Index with expression
var mydict = {['5']: 3}
var val = mydict["$[2+3]"]
echo $val
## STDOUT:
3
## END

#### Copy with a[:]
var a = [1,2,3]
var b = a[:]
= b
## STDOUT:
(List)   [1, 2, 3]
## END

#### Slices with Multiple Dimensions (for QTT)

qtt pretty :mytable <<< '''
name  age:Int
alice 42
bob   31
carol 20
'''

# Cut off the first two rows
var t1 = mytable[2:, :]
= t1

var t2 = mytable[:2, 3:4]
= t2

var t3 = mytable[:2, %(name age)]
= t3

## STDOUT:
(Str)   'TODO: Table Slicing'
(Str)   'TODO: Table Slicing'
## END

#### Index a list with a range, not a slice.  TODO: Figure out semantics
shopt -s oil:all
var mylist = [1,2,3,4,5]
var r = 1:3
var myslice = mylist[r]
## status: 3
## STDOUT:
TODO
## END

#### List(0:3) should copy the list?
shopt -s oil:all
var mylist = List(0:3)
write @mylist
## STDOUT:
0
1
2
## END

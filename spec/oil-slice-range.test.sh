# Test a[1]

#### ranges have higher precedence than comparison (disabled)

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

#### ranges have lower precedence than bitwise operators
= 3:3|4
## STDOUT:
(xrange)   xrange(3, 7)
## END

#### subscript and range of array
var myarray = @(1 2 3 4)
= myarray[1]
= myarray[1:3]

echo 'implicit'
= myarray[:2]
= myarray[2:]

# Stride not supported
#= myarray[1:4:2]

# Now try omitting smoe
#= myarray[1:4:2]
## STDOUT:
(Str)   '2'
(List)   ['2', '3']
implicit
(List)   ['1', '2']
(List)   ['3', '4']
## END

#### subscript and range of list
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
var myarray = @(1 2 3 4 5)
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

#### Range loop
for (i in 1:3) {
  echo "i = $i"
}
var lower = -3
var upper = 2
for (i in lower:upper) {
  echo $i
}
## STDOUT:
i = 1
i = 2
-3
-2
-1
0
1
## END

#### Explicit range with step
for (i in range(1, 7, 2)) {
  echo $i
}
## STDOUT:
1
3
5
## END

#### Explicit slice with step
shopt -s oil:all
var mylist = [0,1,2,3,4,5,6,7,8]
var x = mylist[slice(1, 7, 2)]
write @x
## STDOUT:
1
3
5
## END

#### Index with a Tuple
var mydict = {[2,3]: 'foo'}
var val = mydict[(2, 3)]
echo $val
# TODO: This should work!
setvar val = mydict[2, 3]
echo $val
## STDOUT:
foo
foo
## END

#### Index with expression
var mydict = {[5]: 3}
var val = mydict[2+3]
echo $val
## STDOUT:
3
## END

#### Copy wtih a[:]
var a = [1,2,3]
var b = a[:]
= b
## STDOUT:
(List)   [1, 2, 3]
## END

#### Slices with Multilple Dimensions (with Table/data frame)

# This parses, but it isn't hashable.  We need a type with operator overloading
# to handle this, which we don't have.
#
# Data frames could be:
#
# df[3:5, :]    rows 3 to 5, all cols
#
# df[3:5, @(name age)]    rows 3 to 5, two cols

#var b = d[3,1:]

# TODO: We don't have col=value syntax
var t = Table()

# Cut off the first two rows
var t1 = t[2:, :]
= t1

var t2 = t[:2, 3:4]
= t2

## STDOUT:
(Str)   'TODO: Table Slicing'
(Str)   'TODO: Table Slicing'
## END

#### Slice with Range
shopt -s oil:all
var mylist = [1,2,3,4,5]
var r = 1:3
var myslice = mylist[r]
write @myslice
## STDOUT:
a
## END

#### Range with list constructor
shopt -s oil:all
var mylist = List(0:3)
write @mylist
## STDOUT:
0
1
2
## END

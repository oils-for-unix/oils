# Test a[1]

#### ranges have higher precedence than comparison
# Python slices are comparable?  Why?
pp 1:3 < 1:4
## STDOUT:
True
## END

#### ranges have lower precedence than bitwise operators
pp 3:3|4
## STDOUT:
xrange(3, 7)
## END

#### subscript and range of array
var myarray = @(1 2 3 4)
pp myarray[1]
pp myarray[1:3]

echo 'implicit'
pp myarray[:2]
pp myarray[2:]

# Stride not supported
#pp myarray[1:4:2]

# Now try omitting smoe
#pp myarray[1:4:2]
## STDOUT:
'2'
['2', '3']
implicit
['1', '2']
['3', '4']
## END

#### subscript and range of list
var mylist = [1,2,3,4]
pp mylist[1]
pp mylist[1:3]

echo 'implicit'
pp mylist[:2]
pp mylist[2:]
## STDOUT:
2
[2, 3]
implicit
[1, 2]
[3, 4]
## END

#### expressions and negative indices
var myarray = @(1 2 3 4 5)
pp myarray[-1]
pp myarray[-4:-2]

echo 'implicit'
pp myarray[:-2]
pp myarray[-2:]
## STDOUT:
'5'
['2', '3']
implicit
['1', '2', '3']
['4', '5']
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
echo @x
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
pp b
## STDOUT:
[1, 2, 3]
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
pp t1

var t2 = t[:2, 3:4]
pp t2

## STDOUT:
'TODO: Table Slicing'
'TODO: Table Slicing'
## END

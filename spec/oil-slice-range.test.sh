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
slice(3, 7, None)
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
'2'
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

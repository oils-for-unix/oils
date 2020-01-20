# Typed arrays

#### integer array
var x = @[1 2 3]
write len=$len(x)
## STDOUT:
len=3
## END

#### string array with command sub, varsub, etc.
shopt -s oil:all

var x = 1
var a = @[$x $(write hi) 'sq' "dq $x"]
write len=$len(a)
write @a
## STDOUT:
len=4
1
hi
sq
dq 1
## END

#### arrays with expressions
shopt -s oil:all

# Does () make makes sense?

var x = 5
var y = 6
var a = @[(x) (x+1) (y*2)]

write len=$len(a)
write @a

## STDOUT:
len=3
5
6
12
## END

#### Empty arrays and using Array[T]
shopt -s oil:all

var b = Array[Bool]()
var i = Array[Int]()

#var f = Array[Float]()
write len=$len(b)
write len=$len(i)

var b2 = Array[Bool]([true, false])
write @b2

#write len=$len(f)
## STDOUT:
len=0
len=0
True
False
## END


#### Arrays from generator expressions
shopt -s oil:all

var b = Array[Bool](true for _ in 1:3)

var i = Array[Int](j+1 for j in 1:3)
#var f = Array[Float](i * 2.5 for i in 1:3)
write @b
write @i
#write @f
## STDOUT:
True
True
2
3
## END

#### Standalone generator expression
var x = (i+1 for i in 1:3)
# This is NOT a list.  TODO: This test is overspecified.
repr x | grep -o '<generator'
write status=$?
## STDOUT:
<generator
status=0
## END

#### typeof should show the type
var b = @[true]
# repr should show the type of the object?
repr b
#typeof b

var empty = @[]
repr empty

## STDOUT:
Array[Bool]
Array[???]  # what should this be?
## END

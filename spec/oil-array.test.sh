# Typed arrays

#### integer array
var x = @[1 2 3]
echo len=$len(x)
## STDOUT:
len=3
## END

#### string array with command sub, varsub, etc.
shopt -s oil:basic

var x = 1
var a = @[$x $(echo hi)]
echo len=$len(a)
echo @a
## STDOUT:
len=2
1
hi
## END

#### arrays with expressions
shopt -s oil:basic

# Does () make makes sense?

var x = 5
var y = 6
var a = @[(x+1) (y*2)]

echo len=$len(a)
echo @a

## STDOUT:
len=2
6
12
## END

#### Empty arrays and using Array[T]
shopt -s oil:basic

var b = Array[Bool]()
var i = Array[Int]()

#var f = Array[Float]()
echo len=$len(b)
echo len=$len(i)

var b2 = Array[Bool]([true, false])
echo @b2

#echo len=$len(f)
## STDOUT:
len=0
len=0
True
False
## END


#### Arrays from generator expressions
shopt -s oil:basic

var b = Array[Bool](true for _ in 1:3)

var i = Array[Int](j+1 for j in 1:3)
#var f = Array[Float](i * 2.5 for i in 1:3)
echo @b
echo @i
#echo @f
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
echo status=$?
## STDOUT:
<generator
status=0
## END

# oil-builtin-funcs.test.sh

# TODO: Test that there are exceptions when there are too many args, etc.

#### Bool()
var a = Bool( @() )
var b = Bool( @(foo) )
echo $a $b
## STDOUT:
False
True
## END

#### Int()
var a = Int("3")
var b = Int("-35")
echo $a $b
## STDOUT:
3
-35
## END

#### Float()
# TODO: This needs a lot more testing, for precision, etc.
var a = Float("1.2")
var b = Float("3.4")
echo $a $b
## STDOUT:
1.2
3.4
## END

#### Str()
# TODO: more testing
var a = Str(5)
var b = Str(42)
echo $a $b
## STDOUT:
5
42
## END

#### Tuple()
# TODO: more testing
var a = Tuple()
echo $a
## STDOUT:
()
## END

#### List()
# TODO: more testing
var a = List(range(3))
echo $a
## STDOUT:
[0, 1, 2]
## END

#### Dict()
# TODO: more testing
var a = Dict()
#repr a
echo $len(a)
## STDOUT:
0
## END

#### join()
var x = @(a b 'c d')

var y = join(x)
argv.py $y

var z = join(x, ":")
argv.py $z
## STDOUT:
['abc d']
['a:b:c d']
## END

#### abs

# Also test smooshing
echo $abs(-5)$abs(-0)$abs(5)
echo $abs(-5) $abs(-0) $abs(5)
## STDOUT:
505
5
0
5
## END

#### any() and all()
var a1 = all( @(yes yes) )
var a2 = all( @(yes '') )
var a3 = all( @('' '') )
# This should be true and false or what?
echo $a1 $a2 $a3
echo __

var x1 = any( @(yes yes) )
var x2 = any( @(yes '') )
var x3 = any( @('' '') )
echo $x1 $x2 $x3

## STDOUT:
True
False
False
__
True
True
False
## END

#### sum()
var start = 42

echo $sum( range(3) )
echo $sum( range(3), start)
echo $sum( range(0), start)
## STDOUT:
3
45
42
## END

#### sorted()
var x = sorted(range(3))
echo @x
## STDOUT:
0
1
2
## END

#### reversed()
var x = reversed(range(3))
echo @x
## STDOUT:
2
1
0
## END

#### enumerate()
echo $enumerate
# TODO: need new for loop syntax
for (i, a in enumerate( @(a b c) )) {
  echo $i $a
}
## STDOUT:
0 a
1 b
2 c
## END

#### zip()
echo $zip
var a = @(1 2 3)
var b = @(a b c)
for (item in zip(a, b)) {
  echo $item
}
## STDOUT:
1 a
2 b
3 c
## END

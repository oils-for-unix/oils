# oil-builtin-funcs.test.sh

# TODO: Test that there are exceptions when there are too many args, etc.

#### bool()
shopt -s all:oil
var a = bool( @() )
var b = bool( @(foo) )
echo $a $b
## STDOUT:
False
True
## END

#### int()
shopt -s all:oil
var a = int("3")
var b = int("-35")
echo $a $b
## STDOUT:
3
-35
## END

#### float()
# TODO: This needs a lot more testing, for precision, etc.
shopt -s all:oil
var a = float("1.2")
var b = float("3.4")
echo $a $b
## STDOUT:
1.2
3.4
## END

#### str()
# TODO: more testing
shopt -s all:oil
var a = str(5)
var b = str(42)
echo $a $b
## STDOUT:
5
42
## END

#### tuple()
# TODO: more testing
shopt -s all:oil
var a = tuple()
echo $a
## STDOUT:
()
## END

#### list()
# TODO: more testing
shopt -s all:oil
var a = list(range(3))
echo $a
## STDOUT:
[0, 1, 2]
## END

#### dict()
# TODO: more testing
shopt -s all:oil
var a = dict()
#repr a
echo $len(a)
## STDOUT:
0
## END

#### join()
shopt -s simple_word_eval
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
shopt -s all:oil

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
shopt -s all:oil
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
shopt -s all:oil
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
shopt -s all:oil
var x = sorted(range(3))
echo @x
## STDOUT:
0
1
2
## END

#### reversed()
shopt -s all:oil
var x = reversed(range(3))
echo @x
## STDOUT:
2
1
0
## END

#### enumerate()
echo $enumerate
shopt -s all:oil
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
shopt -s all:oil
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

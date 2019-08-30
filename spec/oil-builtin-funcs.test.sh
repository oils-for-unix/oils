# oil-builtin-funcs.test.sh

# TODO: There will be exceptions when there are too many args.

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

# BUG: These are parsed as 3 word_part of the same word!!!
echo $abs(-5) $abs(-0) $abs(5)
#echo $abs(-5)$abs(-0)$abs(5)
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


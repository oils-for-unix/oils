#### Splice in array
shopt -s oil:basic
var a = %(one two three)
argv.py @a
## STDOUT:
['one', 'two', 'three']
## END

#### Splice in assoc array
shopt -s oil:basic
declare -A A=(['foo']=bar, ['spam']=eggs)
write -- @A | sort
## STDOUT:
foo
spam
## END

#### Can't splice string
shopt -s oil:basic
var mystr = 'abc'
argv.py @mystr
## status: 1
## stdout-json: ""

#### Can't splice undefined
shopt -s oil:basic
argv.py @undefined
echo done
## status: 1
## stdout-json: ""

#### echo $f(x) for various types
shopt -s oil:basic

echo bool $identity(true)
echo int $len(['a', 'b'])
echo float $abs(-3.14)
echo str $identity('identity')

echo ---
echo bool expr $[true]
echo bool splice @identity([true])

## STDOUT:
bool true
int 2
float 3.14
str identity
---
bool expr true
bool splice true
## END

#### echo $f (x) with space is syntax error
shopt -s oil:basic
echo $identity (true)
## status: 2
## STDOUT:
## END

#### echo @f (x) with space is syntax error
shopt -s oil:basic
echo @identity (['foo', 'bar'])
## status: 2
## STDOUT:
## END

#### echo $x for various types
const mybool = true
const myint = 42
const myfloat = 3.14

echo $mybool
echo $myint
echo $myfloat

## STDOUT:
true
42
3.14
## END

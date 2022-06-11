#### Splice in array
shopt -s oil:upgrade
var a = %(one two three)
argv.py @a
## STDOUT:
['one', 'two', 'three']
## END

#### Splice in assoc array
shopt -s oil:upgrade
declare -A A=(['foo']=bar, ['spam']=eggs)
write -- @A
## STDOUT:
foo
spam
## END

#### Can't splice string
shopt -s oil:upgrade
var mystr = 'abc'
argv.py @mystr
## status: 1
## stdout-json: ""

#### Can't splice undefined
shopt -s oil:upgrade
argv.py @undefined
echo done
## status: 1
## stdout-json: ""

#### echo $f(x) for various types
shopt -s oil:upgrade

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

#### echo $f (x) with space is runtime error
shopt -s oil:upgrade
echo $identity (true)
## status: 1
## STDOUT:
## END

#### echo @f (x) with space is runtime error
shopt -s oil:upgrade
echo @identity (['foo', 'bar'])
## status: 1
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

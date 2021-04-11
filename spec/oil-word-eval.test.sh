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
echo int $len(['a', 'b'])
echo float $abs(-3.14)
echo str $identity('identity')

# TODO: There are no builtin functions that return booleans?

## STDOUT:
int 2
float 3.14
str identity
## END


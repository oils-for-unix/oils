#### Splice in array
shopt -s oil:upgrade
var a = %(one two three)
argv.py @a
## STDOUT:
['one', 'two', 'three']
## END

#### Assoc array can't be spliced directly

shopt -s ysh:upgrade
declare -A A=(['foo']=bar ['spam']=eggs)

# Bash behavior is to splice values
write -- "${A[@]}"

write -- @A
echo 'should not get here'

# These should eventually work
#write -- @[A->keys()]
#write -- @[A->values()]

## status: 3
## STDOUT:
bar
eggs
## END

#### Can't splice string
shopt -s oil:upgrade
var mystr = 'abc'
argv.py @mystr
## status: 3
## stdout-json: ""

#### Can't splice undefined
shopt -s oil:upgrade
argv.py @undefined
echo done
## status: 3
## stdout-json: ""

#### echo $[f(x)] for various types
shopt -s oil:upgrade

echo bool $[identity(true)]
echo int $[len(['a', 'b'])]
echo float $[abs(-3.14)]
echo str $[identity('identity')]

echo ---
echo bool expr $[true]
echo bool splice @[identity([true])]

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
## status: 3
## STDOUT:
## END

#### echo @f (x) with space is runtime error
shopt -s oil:upgrade
echo @identity (['foo', 'bar'])
## status: 3
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

#### Wrong sigil with $range() is runtime error
shopt -s oil:upgrade
echo $[10:15]
echo 'should not get here'
## status: 3
## STDOUT:
## END

#### Serializing type in a list
shopt -s oil:upgrade

# If you can serialize the above, then why this?
var mylist = [3, true]

write -- @mylist

write -- ___

var list2 = [List]
write -- @list2

## status: 3
## STDOUT:
3
true
___
## END

#### Wrong sigil @[max(3, 4)]
shopt -s oil:upgrade
write @[max(3, 4)]
echo 'should not get here'
## status: 3
## STDOUT:
## END



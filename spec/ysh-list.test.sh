## our_shell: ysh
## oils_failures_allowed: 1

#### basic array
var x = :| 1 2 3 |
write len=$[len(x)]
## STDOUT:
len=3
## END

#### string array with command sub, varsub, etc.
shopt -s ysh:all

var x = 1
var a = :| $x $(write hi) 'sq' "dq $x" |
write len=$[len(a)]
write @a
## STDOUT:
len=4
1
hi
sq
dq 1
## END

#### printing type of array with pp and =
var b = %(true)
# pp cell should show the type of the object?
pp cell b
= b

var empty = %()
pp cell empty
= empty

## STDOUT:
Array[Bool]
Array[???]  # what should this be?
## END

#### splice and stringify array

shopt -s parse_at

var x = :| 'a b' c |

declare -a array=( @x )

argv.py "${array[@]}"  # should work

echo -$array-  # fails because of strict_arraywith type error

echo -$x-  # fails with type error

## status: 1
## STDOUT:
['a b', 'c']
## END

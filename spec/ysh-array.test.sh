## our_shell: ysh
## oils_failures_allowed: 2

#### basic array
var x = %(1 2 3)
write len=$[len(x)]
## STDOUT:
len=3
## END

#### string array with command sub, varsub, etc.
shopt -s oil:all

var x = 1
var a = %($x $(write hi) 'sq' "dq $x")
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

var x = :| 'a b' c |

argv.py "${x[@]}"  # should work

echo -$x-  # fails because it's not an array

## STDOUT:
['a b', 'c']
2023-06 TODO: should fail
## END

## our_shell: ysh
## oils_failures_allowed: 0

#### Basic List, a[42] a['42'] allowed

var x = :| 1 2 3 |
write len=$[len(x)]

pp test_ (x[1])

# Can be int-looking string
pp test_ (x['2'])

# Not allowed
pp test_ (x['zz'])

## status: 3
## STDOUT:
len=3
(Str)   "2"
(Str)   "3"
## END

#### Mutate List entries, a[42] a['42'] allowed

var a = :| 2 3 4 |

setvar a[1] = 1
pp test_ (a)

setvar a['2'] += 5
pp test_ (a)

# Can be int-looking string
setvar a['2'] = 99
pp test_ (a)

# Not allowed
setvar a['zz'] = 101

## status: 3
## STDOUT:
(List)   ["2",1,"4"]
(List)   ["2",1,9]
(List)   ["2",1,99]
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

#### Can print type of List with pp

var b = :|true|  # this is a string
pp test_ (b)

# = b

var empty = :||
pp test_ (empty)

# = empty

## STDOUT:
(List)   ["true"]
(List)   []
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

#### List->extend()
var l = list(1..<3)
echo $[len(l)]
call l->extend(list(3..<6))
echo $[len(l)]
## STDOUT:
2
5
## END

#### List append()/extend() should return null
shopt -s ysh:all
var l = list(1..<3)

var result = l->extend(list(3..<6))
assert [null === result]

setvar result = l->append(6)
assert [null === result]

echo pass
## STDOUT:
pass
## END

#### List pop()
shopt -s ysh:all
var l = list(1..<5)
assert [4 === l->pop()]
assert [3 === l->pop()]
assert [2 === l->pop()]
assert [1 === l->pop()]
echo pass
## STDOUT:
pass
## END

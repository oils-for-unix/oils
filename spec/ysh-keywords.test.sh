## our_shell: ysh

#### = to pretty print
= 1 + 2 * 3
## STDOUT:
(Int)   7
## END

#### _ to ignore return value
_ 1 + 2 * 3

var strs = %(a b)
_ len(strs)
_ strs->append('c')
write -- @strs

# integer types too
const L = [5, 6]
_ L->append(7)
write -- @L

write __

_ L->pop()  # could also be pop :L
write -- @L

## STDOUT:
a
b
c
5
6
7
__
5
6
## END

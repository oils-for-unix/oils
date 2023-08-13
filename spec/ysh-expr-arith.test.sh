## oils_failures_allowed: 2

#### Addition, with conversion from string

var i = 1 + 2

var j = ' 2.5 ' + ' 3'

var k = ' 5.0 ' - ' 2.5 '

var n = ' 2  ' * 3 * ' 4 '

write -- $i $j $k $n

## STDOUT:
3
5.5
2.5
24
## END


#### Floating Point Division with /

var i = '1.0' / '0.05'

echo $i

## STDOUT:
20.0
## END


#### Operations That Convert to Integer: // % **

var m = ' 5 ' // 2

var n = ' 5 ' %  2

var p = ' 5 ' ** 2

write -- $m $n $p

## STDOUT:
2
1
25
## END

#### Unary Operations

var a = ~1

var b = -1
var c = -2.3

var d = not true


write -- $a $b $c $d

## STDOUT:
-2
-1
-2.3
false
## END

#### unary ~ applied to bool is not allowed
= ~false
## status: 3
## STDOUT:
## END

#### unary ~ applied to float is not allowed
= ~1.
## status: 3
## STDOUT:
## END

#### unary - applied to bool is not allowed
= ~false
## status: 3
## STDOUT:
## END

#### unary 'not' applied to int is not allowed
= not 1
## status: 3
## STDOUT:
## END

#### unary 'not' applied to float is not allowed
= not 1.
## status: 3
## STDOUT:
## END

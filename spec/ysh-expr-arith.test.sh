#### Binary operators, with conversions from string

echo ' i  i' $[1 + 2]
echo 'si  i' $['1' + 2]
echo ' i si' $[1 + '2']
echo ---

echo ' f  f' $[2.5 - 1.5]
echo 'sf  f' $['2.5' - 1.5]
echo ' f sf' $[2.5 - '1.5']
echo ---

echo ' i  f' $[4 * 1.5]
echo 'si  f' $['4' * 1.5]
echo ' i sf' $[4 * '1.5']
echo ---

echo ' f  i' $[5.0 / 2]
echo 'sf  i' $['5.0' / 2]
echo ' f si' $[5.0 / '2']

## STDOUT:
 i  i 3
si  i 3
 i si 3
---
 f  f 1.0
sf  f 1.0
 f sf 1.0
---
 i  f 6.0
si  f 6.0
 i sf 6.0
---
 f  i 2.5
sf  i 2.5
 f si 2.5
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

#### Division by zero
shopt -s parse_brace

try {
  = 42 / 0
}
echo "status / is $_status"

try {
  = 42 // 0
}
echo "status // is $_status"

try {
  = 42 % 0
}
echo "status % is $_status"

## STDOUT:
status / is 3
status // is 3
status % is 3
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


#### unary minus on strings
json write (-3)
json write (-'4')
json write (-'5.5')

# Not accepted
json write (-'abc')

## status: 3
## STDOUT:
-3
-4
-5.5
## END

#### unary ~ complement on strings
json write (~0)
json write (~'1')
json write (~' 2 ')
# Not accepted
json write (~'3.5')

## status: 3
## STDOUT:
-1
-2
-3
## END

#### unary ~ doesn't work on bool
= ~false
## status: 3
## STDOUT:
## END

#### unary ~ doesn't work on float
= ~1.
## status: 3
## STDOUT:
## END

#### unary - applied to bool is not allowed
= ~false
## status: 3
## STDOUT:
## END

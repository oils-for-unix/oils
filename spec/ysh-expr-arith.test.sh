## oils_failures_allowed: 1

#### Minus operator is left associative

var a = 1 - 0 - 1
var b = (1 - 0) - 1
echo a=$a b=$b

var a = 3 - 1 - 2
var b = (3 - 1) - 2
echo a=$a b=$b

## STDOUT:
a=0 b=0
a=0 b=0
## END

#### Division operators are left associative

var a = 10 / 4 / 2
var b = 10 / 4 / 2
echo a=$a b=$b

var a = 9 // 3 // 3
var b = (9 // 3) // 3
echo a=$a b=$b

var a = 11 % 6 % 3
var b = (11 % 6) % 3
echo a=$a b=$b

## STDOUT:
a=1.25 b=1.25
a=1 b=1
a=2 b=2
## END

#### Exponentiation is right associative

var a = 3 ** 2 ** 2
var b = 3 ** (2 ** 2)
echo a=$a b=$b

## STDOUT:
a=81 b=81
## END

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
shopt -s parse_brace

var m = ' 5 ' // 2

var n = ' 5 ' %  2

var p = ' 5 ' ** 2

write -- $m $n $p

try {
  var z = 'a' // 3
}
echo _status $_status

try {
  var z = 'z' % 3
}
echo _status $_status

## STDOUT:
2
1
25
_status 3
_status 3
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
= ~1.0
## status: 3
## STDOUT:
## END

#### unary - applied to bool is not allowed
= ~false
## status: 3
## STDOUT:
## END

#### Big float constants becomes inf and -inf, tiny become 0.0 and -0.0

$SH -c '
var x = 0.12345
pp line (x)
'
echo float=$?

$SH -c '
# Becomes infinity
var x = 0.123456789e1234567
pp line (x)

var x = -0.123456789e1234567
pp line (x)
'
echo float=$?

$SH -c '
# Becomes infinity
var x = 0.123456789e-1234567
pp line (x)

var x = -0.123456789e-1234567
pp line (x)
'
echo float=$?

## STDOUT:
(Float)   0.12345
float=0
(Float)   INFINITY
(Float)   -INFINITY
float=0
(Float)   0.0
(Float)   -0.0
float=0
## END

#### Int constants bigger than 64 bits

# Decimal
$SH -c '
var x = 1111
pp line (x)
'
echo dec=$?

$SH -c '
var x = 1111_2222_3333_4444_5555_6666
pp line (x)
'
echo dec=$?

# Binary
$SH -c '
var x = 0b11
pp line (x)
'
echo bin=$?

$SH -c '
var x = 0b1111_1111_1111_1111_1111_1111_1111_1111_1111_1111_1111_1111_1111_1111_1111_1111_1111_1111
pp line (x)
'
echo bin=$?

# Octal
$SH -c '
var x = 0o77
pp line (x)
'
echo oct=$?

$SH -c '
var x = 0o1111_2222_3333_4444_5555_6666
pp line (x)
'
echo oct=$?

# Hex
$SH -c '
var x = 0xff
pp line (x)
'
echo hex=$?

$SH -c '
var x = 0xaaaa_bbbb_cccc_dddd_eeee_ffff
pp line (x)
'
echo hex=$?

## STDOUT:
(Int)   1111
dec=0
dec=2
(Int)   3
bin=0
bin=2
(Int)   63
oct=0
oct=2
(Int)   255
hex=0
hex=2
## END

#### 64-bit operations

shopt -s ysh:upgrade

var i = 1 << 32
var s = str(i)

echo "i = $i, s = $s"

if (s ~== i) {
  echo equal
}

## STDOUT:
i = 4294967296, s = 4294967296
equal
## END

#### 64-bit integer doesn't overflow

# same as spec/arith.test.sh case 38

var a= 1 << 31 
echo $a

var b = a + a
echo $b

var c = b + a  
echo $c

var x = 1 << 62
var y = x - 1
echo "max positive = $[ x + y ]"

#echo "overflow $[ x + x ]"

## STDOUT:
2147483648
4294967296
6442450944
max positive = 9223372036854775807
## END


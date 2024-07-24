## oils_failures_allowed: 1

#### Pound char literal (is an integer TODO: could be ord())
const a = #'a'
const A = #'A'
echo "$a $A"
## STDOUT:
97 65
## END

#### The literal #''' isn't accepted (use \' instead)

# This looks too much like triple quoted strings!

echo nope
const bad = #'''
echo "$bad"

## status: 2
## STDOUT:
nope
## END

#### Float Literals with e-1

shopt -s ysh:upgrade
# 1+2 2.3
var x = 1.2 + 23.0e-1  # 3.5
if (3.4 < x and x < 3.6) {
  echo ok
}
## STDOUT:
ok
## END

#### Float Literal with _

shopt -s ysh:upgrade

# 1+2 + 2.3
# add this _ here
var x = 1.2 + 2_3.0e-1  # 3.5
if (3.4 < x and x < 3.6) {
  echo ok
}

## STDOUT:
ok
## END


#### Period requires digit on either side, not 5. or .5
echo $[0.5]
echo $[5.0]
echo $[5.]
echo $[.5]

## status: 2
## STDOUT:
0.5
5.0
## END

#### Big float Literals with _

# C++ issue: we currently print with snprintf %g
# Pars

echo $[42_000.000_500]

echo $[42_000.000_500e1]
echo $[42_000.000_500e-1]

## STDOUT:
42000.0005
420000.005
4200.00005
## END

#### Big floats like 1e309 and -1e309 go to Inf / -Inf

# Notes
# - Python float() and JS parseFloat() agree with this behavior
# - JSON doesn't have inf / -inf

echo $[1e309]
echo $[-1e309]

## STDOUT:
inf
-inf
## END

#### Tiny floats go to zero

shopt -s ysh:upgrade
# TODO: need equivalent of in YSh
# '0' * 309
# ['0'] * 309

# 1e-324 == 0.0 in Python

var zeros = []
for i in (1 .. 324) {
  call zeros->append('0')
}

#= zeros

var s = "0.$[join(zeros)]1"
#echo $s

echo float=$[float(s)]

## STDOUT:
float=0.0
## END


#### INFINITY NAN floatEquals()

echo TODO

## STDOUT:
## END

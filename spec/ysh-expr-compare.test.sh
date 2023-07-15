# spec/oil-expr-compare

#### Exact equality with === and !==
shopt -s oil:all

if (3 === 3) {
  echo 'ok'
}
if (3 === '3') {
  echo 'FAIL'
}

if (3 !== 3) {
  echo 'FAIL'
}
if (3 !== '3') {
  echo 'ok'
}

# dicts
var d1 = {'a': 1, 'b': 2}
var d2 = {'a': 1, 'b': 2}
var d3 = {'a': 1, 'b': 3}
if (d1 === d2) {
  echo 'ok'
}
if (d1 === d3) {
  echo 'FAIL'
}
if (d1 !== d3) {
  echo 'ok'
}

## STDOUT:
ok
ok
ok
ok
## END

#### Approximate equality of Str x {Str, Int, Bool} with ~==
shopt -s oil:all

# Note: for now there's no !~== operator.  Use:   not (a ~== b)

if (' foo ' ~== 'foo') {
  echo Str-Str
}
if (' BAD ' ~== 'foo') {
  echo FAIL
}

if ('3 ' ~== 3) {
  echo Str-Int
}
if ('4 ' ~== '3') {
  echo FAIL
}

if (' true ' ~== true) {
  echo Str-Bool
}
if (' true ' ~== false) {
  echo FAIL
}

const matrix = [
  ' TRue ' ~== true,  # case insentiive
  ' FALse ' ~== false,
]

# = matrix
if (matrix === [true, true]) {
  echo 'bool matrix'
}

## STDOUT:
Str-Str
Str-Int
Str-Bool
bool matrix
## END

#### Wrong Types with ~==
shopt -s oil:all

# The LHS side should be a string

echo one
if (['1'] ~== ['1']) {
  echo bad
}
echo two

if (3 ~== 3) {
  echo bad
}

## status: 1
## STDOUT:
one
## END


#### Equality of ~== with Float (deferred)
shopt -s oil:all

if (42 ~== 42.0) {
  echo int-float
}
if (42 ~== 43.0) {
  echo FAIL
}

if ('42' ~== 42.0) {
  echo str-float
}
if ('42' ~== 43.0) {
  echo FAIL
}

if (42 ~== '42.0') {
  echo int-str-float
}
if (42 ~== '43.0') {
  echo FAIL
}
## STDOUT:
## END


#### Comparison of Int 
shopt -s oil:upgrade

if (1 < 2) {
  echo '<'
}
if (2 <= 2) {
  echo '<='
}
if (5 > 4) {
  echo '>'
}
if (5 >= 5) {
  echo '>='
}

if (2 < 1) {
  echo no
}

## STDOUT:
<
<=
>
>=
## END

#### Comparison of Str does conversion to Int
shopt -s oil:upgrade

if ('2' < '11') {
  echo '<'
}
if ('2' <= '2') {
  echo '<='
}
if ('11' > '2') {
  echo '>'
}
if ('5' >= '5') {
  echo '>='
}

if ('2' < '1') {
  echo no
}

## STDOUT:
<
<=
>
>=
## END


#### Mixed Type Comparison does conversion to Int
shopt -s oil:upgrade

if (2 < '11') {
  echo '<'
}
if (2 <= '2') {
  echo '<='
}
if (11 > '2') {
  echo '>'
}
if (5 >= '5') {
  echo '>='
}

if (2 < '1') {
  echo no
}

## STDOUT:
<
<=
>
>=
## END


#### Invalid String is an error
shopt -s oil:upgrade

if ('3' < 'bar') {
  echo no
}
echo 'should not get here'

## status: 3
## STDOUT:
## END


#### Bool conversion -- explicit allowed, implicit not allowed

shopt -s oil:upgrade

if (Int(false) < Int(true)) {
  echo '<'
}

if (Int(false) <= Int(false) ) {
  echo '<='
}

# JavaScript and Python both have this, but Oil prefers being explicit

if (true < false) {
  echo 'BAD'
}
echo 'should not get here'

## status: 3
## STDOUT:
<
<=
## END


#### Chained Comparisons
shopt -s oil:upgrade
if (1 < 2 < 3) {
  echo '123'
}
if (1 < 2 <= 2 <= 3 < 4) {
  echo '123'
}

if (1 < 2 < 2) {
  echo '123'
} else {
  echo 'no'
}
## STDOUT:
123
123
no
## END

#### Tuple comparison is not allowed

# TODO:
# - tuples aren't hashable, so I think they shouldn't be comparable
# - and probably should just be removed from the language.  JS doesn't have
#   them
#   - I think records and destructuring would be better

shopt -s oil:upgrade

var t1 = 3, 0
var t2 = 4, 0
var t3 = 3, 1

if (t2 > t1) { echo yes1 }
if (t3 > t1) { echo yes2 }
if ( (0,0) > t1) { echo yes3 }

# NOTE: ((0,0)  causes problems -- it looks like a shell statement!
#if ( (0,0) > t1) { echo yes3 }
## STDOUT:
yes1
yes2
## END


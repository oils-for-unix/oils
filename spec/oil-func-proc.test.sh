# Oil Functions

#### Untyped function
func add(x, y) Int {
  echo hi
  return x + y
}
var result = add(42, 1)
echo $result
## STDOUT:
hi
43
## END

#### Typed function
func add(x Int, y Int) Int {
  echo hi
  return x+y
}
var result = add(42, 1)
echo $result
## STDOUT:
hi
43
## END

#### Default values for positional params
shopt -s oil:basic
func add(x Int, y=1, z=1+2*3) {
  return x + y + z
}
echo $add(3)
echo $add(3,4)
echo $add(3,4,5)
## STDOUT:
11
14
12
## END

#### Pass too many positional params (without spread)
shopt -s oil:basic
func add(x, y) {
  return x + y
}
var f = add(1,2,3)
echo $f
## STDOUT:
a
## END

#### Passing named arg
func f(; x=42) {
  echo $x
}
pass f()
pass f(x=99)
## STDOUT:
42
99
## END

#### Func with named param with no default
shopt -s oil:basic
func add(x Int, y Int ; verbose Bool) {
  if (verbose) {
    echo 'verbose'
  }
  return x + y
}
var a = add(3, 2, verbose=true)
echo $a

# crashes
var a = add(3, 2)
echo "shouldn't get here"

# doens't work eyt
#echo $add(3, 2, verbose=true)

## status: 1
## STDOUT:
verbose
5
## END

#### Func with varargs
shopt -s oil:basic
func printf(fmt, ...args) {
  pp fmt
  # Should be a LIST
  pp args
}
pass printf('foo', 'a', 42, null)

## STDOUT:
(str)   'foo'
(tuple)   ('a', 42, None)
## END

#### return expression then return builtin
func f(x) {
  return x + 2*3
}
# this goes in proc
f() {
  local x=42
  return $x
}
var x = f(36)
echo x=$x
f
echo status=$?
## STDOUT:
x=42
status=42
## END

#### open proc (any number of args)
proc f {
  var x = 42
  return x
}
# this gets called with 3 args then?
f a b c
echo status=$?
## STDOUT:
status=42
## END

#### closed proc with no args, passed too many
proc f [] {
  return 42
}
f
echo status=$?

# TODO: This should abort, or have status 1
f a b
echo status=$?

## status: 1
## STDOUT:
status=42
## END

#### proc with explicit args

# doesn't require oil:basic
proc f [x, y, z] {
  echo $x $y $z
  var ret = 42
  return ret  # expression mode
}
# this gets called with 3 args then?
f a b c
echo status=$?
## STDOUT:
a b c
status=42
## END

#### proc with varargs

# TODO: opts goes with this
# var opt = grep_opts.parse(ARGV)
#
# func(**opt)  # Assumes keyword args match?
# parse :grep_opts :opt @ARGV

shopt -s oil:basic

proc f [@names] {
  echo names: @names
}
# this gets called with 3 args then?
f a b c
echo status=$?
## STDOUT:
names:
a
b
c
status=0
## END

#### proc with block arg

# TODO: Test more of this
proc f [x, y, &block] {
  echo hi
}
f a b
## STDOUT:
hi
## END

#### basic lambda
var f = |x| x+1
var y = f(0)
echo $y
echo $f(42)
## STDOUT:
1
43
## END


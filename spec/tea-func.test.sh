# tea functions

#### setvar f()[2] = 42 (setitem)
shopt -s oil:all
shopt -s parse_tea

var mylist = [1,2,3]
func f() {
  return mylist
}
setvar f()[2] = 42
write @mylist
## STDOUT:
1
2
42
## END

#### Untyped func
shopt -s oil:all
shopt -s parse_tea

func add(x, y) Int {
  echo 'hi'
  return x + y
}
var result = add(42, 1)
echo $result
## STDOUT:
hi
43
## END

#### Typed func
shopt -s oil:all
shopt -s parse_tea

func add(x Int, y Int) Int {
  echo 'hi'
  return x+y
}
var result = add(42, 1)
echo $result
## STDOUT:
hi
43
## END

#### func: default values for positional params
shopt -s oil:all
shopt -s parse_tea

func add(x Int, y=1, z=1+2*3) {
  return x + y + z
}
echo $add(3)
echo $add(3,4)
## STDOUT:
11
14
## END

#### pass too many positional params to func (without spread)
shopt -s oil:all
shopt -s parse_tea

func add(x, y) {
  return x + y
}
var f = add(1,2)
echo f=$f
var f = add(1,2,3)
echo $f
## status: 1
## STDOUT:
f=3
## END

#### Positional Spread
shopt -s oil:all
shopt -s parse_tea

func add(x, y, ...args) {
  pp cell ':args'  # This works in Tea too for debugging
  return x + y
}
var args = %[5 6 7 8]
var y = add(...args)
echo y=$y
## STDOUT:
7
8
y=11
## END

#### pass named arg to func
shopt -s oil:all
shopt -s parse_tea

func f(; x=42) {
  echo $x
}
_ f()
_ f(x=99)
## STDOUT:
42
99
## END

#### Func with missing named param with no default
shopt -s oil:all
shopt -s parse_tea

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
## status: 1
## STDOUT:
verbose
5
## END

#### Func passed wrong named param
shopt -s oil:all
shopt -s parse_tea

func add(x, y) {
  return x + y
}
var x = add(2, 3)
echo x=$x
var y = add(2, 3, verbose=true)

## status: 1
## STDOUT:
x=5
## END


#### Named Spread
shopt -s oil:all
shopt -s parse_tea

func add(x, y; verbose=true, ...named) {
  if (verbose) { echo 'verbose' }

  # Can list splatting work in tea?  Maybe it should be 
  #   x = splice(named)
  #   pp cell 'x'
  # Or just  
  #   = named
  #   = splice(named)
  write @named | sort
  return x + y
}
var args = {verbose: false, a: 1, b: 2}
var args2 = {f: 3}
var ret = add(2, 3; ...args, ...args2)
echo ret=$ret
## STDOUT:
a
b
f
ret=5
## END

#### Func with varargs
shopt -s oil:all
shopt -s parse_tea

func printf(fmt, ...args) {
  = fmt
  # Should be a LIST
  = args
}
_ printf('foo', 'a', 42, null)

## STDOUT:
(Str)   'foo'
(Tuple)   ('a', 42, None)
## END

#### return expression then return builtin
shopt -s parse_tea

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

#### inline function calls with spread, named args, etc.
shopt -s oil:all

func f(a, b=0, ...args; c, d=0, ...named) {
  write __ args: @args
  write __ named:
  write @named | sort
  if (named) {
    return [a, b, c, d]
  } else {
    return a + b + c + d
  }
}
var a = [42, 43]
var n = %{x: 99, y: 100}

echo ____
write string $f(0, 1, ...a, c=2, d=3)

# Now get a list back
echo ____
write array @f(5, 6, ...a, c=7, d=8; ...n)

## STDOUT:
____
__
args:
42
43
__
named:

string
6
____
__
args:
42
43
__
named:
x
y
array
5
6
7
8
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

#### Nested functions ???  Bug from Till.
shopt -s oil:all
shopt -s parse_tea

# I think we should disallow these.
# The bug is related to return as a keyword!!!  Which we will get rid of in the
# newer Tea parser.

func returnsString() {
  func unrelated() {return "hm?"}
  return "test" # This fails
}

= returnsString()

## STDOUT:
## END

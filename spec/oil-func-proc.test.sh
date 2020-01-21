# Oil Functions

#### Untyped func
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

#### Typed func
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

#### func: default values for positional params
shopt -s oil:all
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
func add(x, y, ...args) {
  write @args
  return x + y
}
var args = @[5 6 7 8]
var y = add(...args)
echo y=$y
## STDOUT:
7
8
y=11
## END

#### pass named arg to func
func f(; x=42) {
  echo $x
}
pass f()
pass f(x=99)
## STDOUT:
42
99
## END

#### Func with missing named param with no default
shopt -s oil:all
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
func add(x, y; verbose=true, ...named) {
  if (verbose) { echo 'verbose' }
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
func printf(fmt, ...args) {
  = fmt
  # Should be a LIST
  = args
}
pass printf('foo', 'a', 42, null)

## STDOUT:
(Str)   'foo'
(Tuple)   ('a', 42, None)
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

#### Open proc (any number of args)
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

#### Closed proc with no args, passed too many
proc f() {
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

#### Open proc has "$@"
shopt -s oil:all
proc foo { 
  write ARGV "$@"
}
builtin set -- a b c
foo x y z
## STDOUT:
ARGV
x
y
z
## END

#### Closed proc doesn't have "$@"
shopt -s oil:all
proc foo(d, e, f) { 
  write params $d $e $f
  write ARGV "$@"
}
builtin set -- a b c
foo x y z
## STDOUT:
params
x
y
z
ARGV
## END


#### Proc with default args
proc f(x='foo') {
  echo x=$x
}
f
## STDOUT:
x=foo
## END

#### Proc with explicit args

# doesn't require oil:all
proc f(x, y, z) {
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

#### Proc with varargs

# TODO: opts goes with this
# var opt = grep_opts.parse(ARGV)
#
# func(**opt)  # Assumes keyword args match?
# parse :grep_opts :opt @ARGV

shopt -s oil:all

proc f(@names) {
  write names: @names
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

#### Proc name-with-hyphen
proc name-with-hyphen {
  echo "$@"
}
name-with-hyphen x y z
## STDOUT:
x y z
## END

#### Proc with block arg

# TODO: Test more of this
proc f(x, y, &block) {
  echo hi
}
f a b
## STDOUT:
hi
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
var n = {x: 99, y: 100}

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


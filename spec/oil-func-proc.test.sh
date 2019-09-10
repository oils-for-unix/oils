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

#### proc with no args
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

#### proc with explicit args

# doesn't require all:oil
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

#### proc with varargs

# TODO: opts goes with this
# var opt = grep_opts.parse(ARGV)
#
# func(**opt)  # Assumes keyword args match?
# parse :grep_opts :opt @ARGV

proc f(@names) {
  echo names= $names
  return 42
}
# this gets called with 3 args then?
f a b c
echo status=$?
## STDOUT:
names=
a
b
c
status=42
## END

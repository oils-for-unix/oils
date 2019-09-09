# Oil Functions

#### Untyped function
func add(x, y) Int {
  echo hi
  return (x + y)
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
  return (x+y)
}
var result = add(42, 1)
echo $result
## STDOUT:
hi
43
## END

#### return expression then return builtin
func f(x) {
  return (x + 1)
}
# this goes in proc
f() {
  local x=42
  return $x
}
var x = f(41)
echo x=$x
f
echo status=$?
## STDOUT:
x=42
status=42
## END

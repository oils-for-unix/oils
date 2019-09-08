# Oil Functions

#### Untyped function
func add(x, y) Int {
  echo hi
  return $x
}
var result = add(42, 1)
echo $result
## STDOUT:
hi
42
## END

#### Typed function
func add(x Int, y Int) Int {
  echo hi
  return $x
}
var result = add(42, 1)
echo $result
## STDOUT:
## END

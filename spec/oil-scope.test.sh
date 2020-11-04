# Demonstrations for users.  Could go in docs.

#### GetVar scope and shopt --unset dynamic_scope
f() {
  echo "f x=$x"
}

f1() {
  local x=43
  f
}

proc p {
  echo "p x=$x"
}

p1() {
  local x=43
  p
}

x=42
f1
p1

shopt --unset dynamic_scope
f1

## STDOUT:
f x=43
p x=42
f x=42
## END


#### SetVar scope and shopt --unset dynamic_scope
f() {
  x=f
  echo "f x=$x"
}

# I think you're supposed to use setglobal x = 'p' here?
# Should the old kind of assignment be a failure?
# Yeah because it was confusing that x=1 is a global assignment.
proc p {
  x=p
  echo "p x=$x"
}

x=42
echo x:$x

f
echo x:$x

p
echo x:$x

shopt --unset dynamic_scope
f
echo x:$x

## STDOUT:
x:42
f x=f
x=f

x=p

## END

#### read scope
echo 42 | read x

## STDOUT:
x=42
x=
## END

#### getopts scope
getopts 'x:' x -x 42
echo x=$x

## STDOUT:
x=42
x=
## END

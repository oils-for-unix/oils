# Demonstrations for users.  Could go in docs.

#### GetVar scope and shopt --unset dynamic_scope
f() {
  echo "f x=$x"
}

proc p {
  echo "p x=$x"
}

x=42
f
p

shopt --unset dynamic_scope
f

## STDOUT:
f x=42
p x=
f x=
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

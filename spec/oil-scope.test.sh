# Demonstrations for users.  Could go in docs.

#### GetValue scope and shopt --unset dynamic_scope

f() {
  echo "sh x=$x"
}

proc p {
  echo "oil x=$x"
}

demo() {
  local x=dynamic
  f
  p

  shopt --unset dynamic_scope
  f
}

x=global
demo
echo x=$x

## STDOUT:
sh x=dynamic
oil x=global
sh x=global
x=global
## END


#### SetValue scope and shopt --unset dynamic_scope
f() {
  x=f
}

proc p {
  x=p
}

demo() {
  local x=stack
  echo x=$x
  echo ---

  f
  echo f x=$x

  x=stack
  p
  echo p x=$x

  shopt --unset dynamic_scope
  x=stack
  f
  echo funset x=$x
}

x=global
demo

echo ---
echo x=$x

## STDOUT:
x=stack
---
f x=f
p x=stack
funset x=stack
---
x=f
## END

#### read scope (setref)
read-x() {
  echo new | read x
}
demo() {
  local x=42
  echo x=$x
  read-x
  echo x=$x
}
demo
echo x=$x

echo ---

shopt --unset dynamic_scope  # should NOT affect read
demo
echo x=$x

## STDOUT:
x=42
x=new
x=
---
x=42
x=new
x=
## END

#### printf -v scope (setref)
set-x() {
  printf -v x "%s" new
}
demo() {
  local x=42
  echo x=$x
  set-x
  echo x=$x
}
demo
echo x=$x

echo ---

shopt --unset dynamic_scope  # should NOT affect read
demo
echo x=$x

## STDOUT:
x=42
x=new
x=
---
x=42
x=new
x=
## END

#### ${undef=a} and shopt --unset dynamic_scope

set-x() {
  : ${x=new}
}
demo() {
  local x
  echo x=$x
  set-x
  echo x=$x
}

demo
echo x=$x

echo ---

# Now this IS affected?
shopt --unset dynamic_scope 
demo
echo x=$x
## STDOUT:
x=
x=new
x=
---
x=
x=
x=
## END

#### declare -p respects it
__g=G
show-vars() {
  local __x=X
  declare -p | grep '__'
  echo status=$?

  echo -
  declare -p __y | grep '__'
  echo status=$?
}

demo() {
  local __y=Y

  show-vars
  echo ---
  shopt --unset dynamic_scope
  show-vars
}

demo

## STDOUT:
declare -- __g=G
declare -- __x=X
declare -- __y=Y
status=0
-
declare -- __y=Y
status=0
---
declare -- __g=G
declare -- __x=X
status=0
-
status=1
## END



#### unset composes because it uses dynamic scope (even in Oil)
shopt -s oil:all

proc unset-two {
  unset $1 
  unset $2
}

demo() {
  local x=X
  local y=Y

  echo "x=$x y=$y"

  unset-two x y

  shopt --unset nounset
  echo "x=$x y=$y"
}

demo
## STDOUT:
x=X y=Y
x= y=
## END


#### SetLocalShopt constructs

f() {
  (( x = 42 ))
}
demo() {
  f
  echo x=$x
}

demo

echo ---

shopt --unset dynamic_scope

unset x

demo

echo --- global
echo x=$x
## STDOUT:
x=42
---
x=
--- global
x=
## END

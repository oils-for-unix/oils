## oils_failures_allowed: 1

# Demonstrations for users.  Could go in docs.

#### GetValue scope and shopt --unset dynamic_scope
shopt --set parse_proc

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
shopt --set parse_proc

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
x=global
## END

#### read scope (setref)
set -o errexit

read-x() {
  echo dynamic-scope | read x
}
demo() {
  local x=42
  echo x_before=$x
  read-x
  echo x_after=$x
}
demo
echo x=$x

echo ---

# Now 'read x' creates a local variable
shopt --unset dynamic_scope
demo
echo x=$x

## STDOUT:
x_before=42
x_after=dynamic-scope
x=
---
x_before=42
x_after=42
x=
## END

#### printf -v x respects dynamic_scope
set -o errexit

set-x() {
  printf -v x "%s" dynamic-scope
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
x=dynamic-scope
x=
---
x=42
x=42
x=
## END

#### printf -v a[i] respects dynamic_scope
set -o errexit

set-item() {
  printf -v 'a[1]' "%s" dynamic-scope
}
demo() {
  local -a a=(41 42 43)
  echo "a[1]=${a[1]}"
  set-item
  echo "a[1]=${a[1]}"
}
demo
echo "a[1]=${a[1]}"

echo ---

shopt --unset dynamic_scope  # should NOT affect read
demo
echo "a[1]=${a[1]}"

## STDOUT:
a[1]=42
a[1]=dynamic-scope
a[1]=
---
a[1]=42
a[1]=42
a[1]=
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


#### OshLanguageSetValue constructs

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


#### shell assignments 'neutered' inside 'proc'
shopt --set parse_proc

# They can't mutate globals or anything higher on the stack

proc p {
  g=PROC
  export e=PROC
}

f() {
  g=SH
  export e=SH
}

e=E
g=G
p
echo e=$e g=$g

p
echo e=$e g=$g

f
echo e=$e g=$g

## STDOUT:
e=E g=G
e=E g=G
e=SH g=SH
## END

#### setglobal still allows setting globals
shopt --set parse_proc

proc p {
  setglobal new_global = 'p'
  setglobal g = 'p'
}

var g = 'G'

p

echo g=$g new_global=$new_global
## STDOUT:
g=p new_global=p
## END

#### setref with out Ref param
shopt --set parse_proc

proc set-it(s Ref, val) {
  # s param is rewritten to __s to avoid name conflict
  #pp cell __s
  setref s = "foo-$val"
}

proc demo {
  if true; then
    var s = 'abc'
    set-it :s SS
    echo $s
  fi

  var t = 'def'
  set-it :t TT
  echo $t
}

demo

## STDOUT:
foo-SS
foo-TT
## END

#### setref with conflicting variable name
shopt --set parse_proc

proc set-it(s Ref, val) {
  #pp cell __s

  # This breaks it!
  var oops = ''
  setref s = "foo-$val"
}

proc demo {
  var oops = ''
  set-it :oops zz
  echo oops=$oops
}

demo

## STDOUT:
oops=foo-zz
## END


#### setref of regular param is a fatal error
shopt --set parse_proc

proc set-it(s Ref, val) {
  setref val = 'oops'
}

var s = 'abc'
set-it :s SS
echo $s

## status: 1
## STDOUT:
## END

#### setref equivalent without pgen2 syntax, using open proc
shopt --set parse_proc

# This is kind of what we compile to.  Ref params get an extra __ prefix?  then
# that means you can't really READ them either?  I think that's OK.

# At call time, param binding time:
#   If the PARAM has a colon prefix:
#     Assert that the ARG has a colon prefix.  Don't remove it.
#     Set the cell.nameref flag.
#
# At Setref time:
#   Check that it's cell.nameref.
#   Add extra : to lvalue.{Named,Indexed,Keyed} and perform it.
#
# The __ avoids the nameref cycle check.
# And we probably disallow reading from the ref.  That's OK.  The caller can
# pass it in as a regular value!

proc set-it {
  local -n __s=$1  # nameref flag needed with setref
  local val=$2

  # well this part requires pgen2
  setref s = "foo-$val"
}

var s = 'abc'
var t = 'def'
set-it s SS
set-it t TT  # no colon here
echo $s
echo $t

## STDOUT:
foo-SS
foo-TT
## END

#### setref a, b = 'one', 'two'
shopt --set parse_proc

proc p(x, a Ref, b Ref) {
  setref a, b = "${x}1", "${x}2"
}

p foo :c :d
echo c=$c d=$d
## STDOUT:
c=foo1 d=foo2
## END

#### setref a[i]

# You can do this in bash/mksh.  See nameref!

shopt --set parse_proc

proc set1(a Ref, item) {
  setref a[1] = item
}

var a = %(one two three)
var myarray = %(a b c)

set1 :a zzz
set1 :myarray z

shopt --set oil:upgrade
#write -- @a
write -- @myarray

## STDOUT:
a
z
c
## END

#### unset inside proc uses local scope
shopt --set parse_brace
shopt --set parse_proc

f() {
  unset x
}

proc p() {
  unset x
}

proc p2() {
  shopt --set dynamic_scope {  # turn it back on
    unset x
  }
}

x=foo
f
echo f x=$x

x=bar
p
echo p x=$x

x=spam
p2
echo p2 x=$x

## STDOUT:
f x=
p x=bar
p2 x=
## END

#### unset composes when you turn on dynamic scope
shopt -s oil:all

proc unset-two {
  shopt --set dynamic_scope {
    unset $1 
    unset $2
  }
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

#### Temp Bindings
shopt --set parse_proc

myfunc() {
  echo myfunc FOO=$FOO
}
proc myproc() {
  echo myproc FOO=$FOO
}

FOO=bar myfunc
FOO=bar myproc
FOO=bar echo inline FOO=$FOO
FOO=bar printenv.py FOO

## STDOUT:
myfunc FOO=bar
myproc FOO=
inline FOO=
bar
## END

#### cd blocks don't introduce new scopes
shopt --set oil:upgrade

var x = 42
cd / {
  var y = 0
  var z = 1
  echo $x $y $z
  setvar y = 43
}
setvar z = 44
echo $x $y $z

## STDOUT:
42 0 1
42 43 44
## END

#### IFS=: myproc exports when it doesn't need to
shopt --set parse_proc
shopt --set parse_brace

s='xzx zxz'

myfunc() {
  echo myfunc IFS="$IFS"
  argv.py $s
}

proc myproc() {
  echo myproc IFS="$IFS"
  argv.py $s
}

IFS=: $REPO_ROOT/spec/bin/printenv.py IFS

# default value
echo "$IFS" | od -A n -t x1

IFS=' z'
echo IFS="$IFS"

IFS=' x' myfunc

# Problem: $IFS in procs only finds GLOBAL values.  But when actually
# splitting, $IFS is a 'shvar' which respects DYNAMIC scope.
# - TODO: shvar_get('IFS')

IFS=' x' myproc

# Oil solution to the problem
shvar IFS=' x' {
  myproc
}

## STDOUT:
:
 20 09 0a 0a
IFS= z
myfunc IFS= x
['', 'z', 'z', 'z']
myproc IFS= z
['', 'z', 'z', 'z']
myproc IFS= x
['', 'z', 'z', 'z']
## END

#### shvar usage 
shopt --set oil:upgrade
shopt --unset errexit

# no block
shvar
echo status=$?

shvar {  # no arg
  true
}
echo status=$?

shvar foo {  # should be name=value
  true
}
echo status=$?
## STDOUT:
status=2
status=2
status=2
## END

#### shvar global
shopt --set oil:upgrade
shopt --unset nounset

echo _ESCAPER=$_ESCAPER
echo _DIALECT=$_DIALECT

shvar _ESCAPER=html _DIALECT=ninja {
  echo block _ESCAPER=$_ESCAPER
  echo block _DIALECT=$_DIALECT
}

echo _ESCAPER=$_ESCAPER
echo _DIALECT=$_DIALECT

# Now set them
_ESCAPER=foo
_DIALECT=bar

echo ___

echo _ESCAPER=$_ESCAPER
echo _DIALECT=$_DIALECT

shvar _ESCAPER=html _DIALECT=ninja {
  echo block _ESCAPER=$_ESCAPER
  echo block _DIALECT=$_DIALECT

  shvar _ESCAPER=nested {
    echo nested _ESCAPER=$_ESCAPER
    echo nested _DIALECT=$_DIALECT
  }
}

echo _ESCAPER=$_ESCAPER
echo _DIALECT=$_DIALECT

## STDOUT:
_ESCAPER=
_DIALECT=
block _ESCAPER=html
block _DIALECT=ninja
_ESCAPER=
_DIALECT=
___
_ESCAPER=foo
_DIALECT=bar
block _ESCAPER=html
block _DIALECT=ninja
nested _ESCAPER=nested
nested _DIALECT=ninja
_ESCAPER=foo
_DIALECT=bar
## END

#### shvar local
shopt --set oil:upgrade  # blocks
shopt --unset simple_word_eval  # test word splitting

proc foo {
  shvar IFS=x MYTEMP=foo {
    echo IFS="$IFS"
    argv.py $s
    echo MYTEMP=${MYTEMP:-undef}
  }
}
var s = 'a b c'
argv.py $s
foo
argv.py $s
echo MYTEMP=${MYTEMP:-undef}
## STDOUT:
['a', 'b', 'c']
IFS=x
['a b c']
MYTEMP=foo
['a', 'b', 'c']
MYTEMP=undef
## END

#### shvar IFS
shopt --set oil:upgrade

proc myproc() {
  echo "$IFS" | od -A n -t x1

  local mylocal=x
  shvar IFS=w {
    echo inside IFS="$IFS"
    echo mylocal="$mylocal"  # I do NOT want a new scope!
  }
  echo "$IFS" | od -A n -t x1
}

myproc
## STDOUT:
 20 09 0a 0a
inside IFS=w
mylocal=x
 20 09 0a 0a
## END

#### shvar_get()
shopt --set parse_proc

s='xzx zxz'

proc myproc {
  echo wrong IFS="$IFS"         # NOT what's used
  echo shvar IFS=$[shvar_get('IFS')]  # what IS used: dynamic scope
  argv.py $s
}

IFS=x
IFS=z myproc
## STDOUT:
wrong IFS=x
shvar IFS=z
['x', 'x ', 'x']
## END

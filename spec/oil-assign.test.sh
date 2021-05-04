# Test var / setvar / etc.

# TODO: GetVar needs a mode where Obj[str] gets translated to value.Str?
# Then all code will work.
#
# word_eval:
#
# val = self.mem.GetVar(var_name) ->
# val = GetWordVar(self.mem, var_name)
#
# Conversely, in oil_lang/expr_eval.py:
# LookupVar gives you a plain Python object.  I don't think there's any
# downside here.
#
# pp exposes the differences.
#
# Notes:
#
# - osh/cmd_exec.py handles OilAssign, which gets wrapped in value.Obj()
# - osh/word_eval.py _ValueToPartValue handles 3 value types.  Used in:
#   - _EvalBracedVarSub
#   - SimpleVarSub in _EvalWordPart
# - osh/expr_eval.py: _LookupVar wrapper should disallow using Oil values
#   - this is legacy stuff.  Both (( )) and [[ ]]
#   - LhsIndexedName should not reference Oil vars either


#### integers expression and augmented assignment
var x = 1 + 2 * 3
echo x=$x

setvar x += 4
echo x=$x
## STDOUT:
x=7
x=11
## END

#### proc static check: const can't be mutated
proc f {
  const x = 'local'
  echo x=$x
  setvar x = 'mutated'
  echo x=$x
}
## status: 2
## STDOUT:
## END

#### top-level dynamic check: const can't be be mutated
shopt -s oil:all

x = 'foo'
echo x=$x
const x = 'bar'
echo x=$x
## status: 1
## STDOUT:
x=foo
## END

#### top level: var can be redefined
var x = "global"
echo x=$x
f() {
  var x = "local"
  echo x=$x
}
f
var x = "g2"
echo x=$x
## status: 0
## STDOUT:
x=global
x=local
x=g2
## END


#### setvar mutates local
proc f {
  var x = 'local'
  echo x=$x
  setvar x = 'mutated'
  echo x=$x
}

var x = 'global'
echo x=$x
f
echo x=$x
## STDOUT:
x=global
x=local
x=mutated
x=global
## END

#### setvar CREATES global
setvar x = 'global'
echo x=$x
## STDOUT:
x=global
## END

#### setvar modified local or global scope
modify_with_shell_assignment() {
  f=shell
}

modify_with_setvar() {
  setvar f = "setvar"
}

f() {
  var f = 1
  echo f=$f
  modify_with_shell_assignment
  echo f=$f

  # modifies the GLOBAL, not the one in parent scope
  modify_with_setvar
  echo f=$f
  setvar f = 'local'
  echo f=$f
}
var f = 'outer'
echo f=$f
f
echo f=$f
## STDOUT:
f=outer
f=1
f=shell
f=shell
f=local
f=setvar
## END

#### setlocal when variable isn't declared results in fatal error
shopt -s oil:all

var x = 1
f() {
  # setting global is OK
  setglobal x = 'XX'
  echo x=$x

  # setvar CREATES a variable
  setvar y = 'YY'
  echo y=$y

  setlocal z = 3  # NOT DECLARED
  echo z=$z
}
## status: 2
## STDOUT:
## END

#### setlocal works (with bin/osh, no shopt)
proc p {
  var x = 5
  echo $x
  setlocal x = 42
  echo $x
}
p
## STDOUT:
5
42
## END

#### setlocal at top level
var x = 1
setlocal x = 42  # this is allowed
echo $x
setlocal y = 50  # error because it's not declared
## status: 2
## STDOUT:
42
## END

#### setlocal doesn't mutate globals
proc p() {
  var g = 1
  setlocal g = 2
}
var g = 42
p
echo $g
## STDOUT:
42
## END

#### setglobal
f() {
  var x = 'local'
  echo x=$x
  setglobal x = 'mutated'
}
var x = 'global'
echo x=$x
f
echo x=$x
## STDOUT:
x=global
x=local
x=mutated
## END

#### setglobal of undeclared var is allowed
var x = 'XX'
echo x=$x
setglobal x = 'xx'
echo x=$x

# fatal error
setglobal y = 'YY'

## STDOUT:
x=XX
x=xx
## END

#### var/setvar x, y = 1, 2

# Python doesn't allow you to have annotation on each variable!
# https://www.python.org/dev/peps/pep-0526/#where-annotations-aren-t-allowed
var x Int, y Int = 3, 4
echo x=$x y=$y

setvar x, y = 1, 9
echo x=$x y=$y

setvar y, x = x, y
echo x=$x y=$y

## STDOUT:
x=3 y=4
x=1 y=9
x=9 y=1
## END

#### setvar d->key = 42 (setitem)
shopt -s oil:all

var d = {}
setvar d['f2'] = 42
setvar d->f3 = 43

# Use the opposite thing to retrieve
var f3 = d['f3']
var f2 = d->f2
echo f3=$f3
echo f2=$f2
## STDOUT:
f3=43
f2=42
## END

#### setvar mylist[1] = 42 (setitem)
shopt -s oil:all
var mylist = [1,2,3]
setvar mylist[1] = 42

write  -sep ' ' @mylist
## STDOUT:
1 42 3
## END

#### setvar obj.attr = 42 (setattr)
shopt -s oil:all

# TODO: dicts and list can't have arbitrary attributes set.  But right now
# regex objects can.  Should we change that?

var myobj = /d+/

setvar myobj.x = 42
var val = myobj.x
echo val=$val
## STDOUT:
val=42
## END

#### mixing assignment builtins and Oil assignment
shopt -s oil:all

proc local-var {
  local x=1
  var x = 2
  echo x=$x
}

proc readonly-const {
  readonly x=1
  x = 2
  echo x=$x
}

run --assign-status :st eval 'local-var'
echo status=$st
run --assign-status :st eval 'readonly-const' || true
echo status=$st

## STDOUT:
x=2
status=0
status=1
## END

#### setref out = 'YY'
proc p (s, :out) {
  setref out = 'YY'
}
var x = 'XX'
echo x=$x
p abcd :x
echo x=$x

p zz :undefined_var
echo u=$undefined_var

## STDOUT:
x=XX
x=YY
u=YY
## END

#### circular dict
var d = {name: 'foo'}
= d
setvar d['name'] = 123
= d
setvar d['name'] = 'mystr'
= d
setvar d['name'] = d
= d
## STDOUT:
(Dict)   {'name': 'foo'}
(Dict)   {'name': 123}
(Dict)   {'name': 'mystr'}
(Dict)   {'name': {...}}
## END

#### circular list
var L = [1,2,3]
= L
setvar L[0] = L
= L
## STDOUT:
(List)   [1, 2, 3]
(List)   [[...], 2, 3]
## END


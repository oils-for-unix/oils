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
# repr exposes the differences.
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

#### const can't be mutated
proc f {
  const x = 'local'
  echo x=$x
  setvar x = 'mutated'
  echo x=$x
}
var x = 'global'
echo x=$x
f
echo x=$x
## status: 1
## STDOUT:
x=global
x=local
## END

#### const can't be redeclared
shopt -s oil:all

x = 'foo'
echo x=$x
const x = 'bar'
echo x=$x
## status: 1
## STDOUT:
x=foo
## END

#### 'setvar' mutates local
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

#### 'setvar' CREATES global
setvar x = 'global'
echo x=$x
## STDOUT:
x=global
## END

#### 'set' when variable isn't declared results in fatal error
shopt -s oil:all

var x = 1
f() {
  # setting global is OK
  setglobal x = 'XX'
  echo x=$x

  # setvar CREATES a variable
  setvar y = 'YY'
  echo y=$y

  set z = 3  # NOT DECLARED
  echo z=$z
}
f
## status: 1
## STDOUT:
x=XX
y=YY
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

#### setglobal of undeclared var is an error
var x = 'XX'
echo x=$x
setglobal x = 'xx'
echo x=$x

# fatal error
setglobal y = 'YY'

## status: 1
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

#### setvar f()[2] = 42 (setitem)
shopt -s oil:all

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

#### duplicate var def results in fatal error
var x = "global"
f() {
  var x = "local"
  echo x=$x
}
f
var x = "redeclaration is an error"
## status: 1
## STDOUT:
x=local
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

#### setref (not implemented)

# TODO: should be :out (rather than out Ref, because procs have no types?)
# or (out Ref, b Block) ?
proc p (s, out) {
  setref out = 'YY'
}
var x = 'XX'
echo x=$x
p abcd :x
echo x=$x
## STDOUT:
x=XX
x=YY
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



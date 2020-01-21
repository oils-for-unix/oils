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

#### setvar when variable isn't declared results in fatal error
var x = 1
f() {
  # setting global is OK
  setvar x = 2
  echo x=$x

  setvar y = 3  # NOT DECLARED
  echo y=$y
}
f
## status: 1
## STDOUT:
x=2
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

#### setvar dynamic scope (TODO: change this?)
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
  modify_with_setvar
  echo f=$f
}
f
## STDOUT:
f=1
f=shell
f=setvar
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


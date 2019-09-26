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
#var x Int, y Int = 3, 4
setvar x, y = 1, 2
echo $x $y
## STDOUT:
1 2
## END

#### setvar x[1] = 42
shopt -s oil:basic
var mylist = [1,2,3]
setvar x[1] = 42
echo -sep ' ' @x
## STDOUT:
1 42 3
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


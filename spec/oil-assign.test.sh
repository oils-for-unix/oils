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
shopt -s oil:all parse_equals

x = 'foo'
echo x=$x
const x = 'bar'
echo x=$x
## status: 1
## STDOUT:
x=foo
## END

#### top level: var can be redefined by var/const
var x = "global"
echo x=$x
f() {
  var x = "local"
  echo x=$x
}
f
var x = "g2"
echo x=$x
const x = 'now-const'
echo x=$x
const x = 'oops'
echo x=$x
## status: 1
## STDOUT:
x=global
x=local
x=g2
x=now-const
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

#### top level: setvar creates global
setvar x = 'global'
echo x=$x
setvar x = 'g2'
echo x=$x
## STDOUT:
x=global
x=g2
## END

#### top level: setvar mutates var
var x = 1
setvar x = 42  # this is allowed
echo $x
setvar y = 50  # error because it's not declared
echo $y
## STDOUT:
42
50
## END

#### proc static check: variable changed by setvar must be declared
shopt -s oil:all

var x = 1
f() {
  # setting global is OK
  setglobal x = 'XX'
  echo x=$x

  # local NOT DECLARED
  setvar x = 'YY'
  echo y=$y
}
## status: 2
## STDOUT:
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

write --sep ' ' @mylist
## STDOUT:
1 42 3
## END

#### mixing assignment builtins and Oil assignment
shopt -s oil:all parse_equals

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

try eval 'local-var'
echo status=$_status
try eval 'readonly-const'
echo status=$_status

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

#### setref composes: 2 levels deep
proc q(s, :out) {
  echo "q s=$s"
  setref out = 'YY'
}
proc p(:out) {
  # NOTE: This doesn't work
  # q dummy :out
  var tmp = ''
  q dummy :tmp
  setref out = tmp
}

var x = 'XX'
echo x=$x
p :x
echo x=$x

## STDOUT:
x=XX
q s=dummy
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


#### exit code of var, const, setvar with command sub

# NOTE: This feels PROBLEMATIC without command_sub_errexit feels like it should
# be the last one ...

$SH -c '
var x = $(false)
echo inside=$?
'
echo outside=$?

$SH -c '
setvar x = $(false)
echo inside=$?
'
echo outside=$?

# Argument list
$SH -c '
_ split( $(false) )
echo inside=$?
'
echo outside=$?

# Place expression
$SH -c '
var d = {}
setvar d[ $(false) ] = 42
echo inside=$?
'
echo outside=$?

## STDOUT:
outside=1
outside=1
outside=1
outside=1
## END


#### Bare Assignment Does Dynamic Checks, not Static
shopt --set parse_equals

proc bare {
  x = 3
  echo x=$x
  x = 4  # already defined
  echo x=$x
}

bare

# Compare with this STATIC check
proc myconst {
  # const x = 3
  # const x = 4  # already defined
  echo x=$x
}

## status: 1
## STDOUT:
x=3
## END

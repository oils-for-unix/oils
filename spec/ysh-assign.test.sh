# Test var / setvar / etc.

## our_shell: ysh
## oils_failures_allowed: 2


# TODO: GetVar needs a mode where Obj[str] gets translated to value.Str?
# Then all code will work.
#
# word_eval:
#
# val = self.mem.GetVar(var_name) ->
# val = GetWordVar(self.mem, var_name)
#
# Conversely, in ysh/expr_eval.py:
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


#### Augmented assignment doesn't work on shell arrays

# I suppose the logic is that string and array concat is ++
#
# I wonder if a ++= operator makes sense?

shopt -s parse_at simple_word_eval
var x = %(a 'b c')
argv.py @x

setvar x += %(d e)  # fatal error
argv.py @x
## status: 3
## STDOUT:
['a', 'b c']
## END


#### Augmented assignment with integers
var x = 1 + 2 * 3
echo x=$x

setvar x += 4 * 1
echo x=$x
## STDOUT:
x=7
x=11
## END

#### Augmented assignment on string changes to integer

var x = '42'
= x

setvar x += 4 * 1
= x

setvar x += '9'
= x

## STDOUT:
(Str)   '42'
(Int)   46
(Int)   55
## END

#### Augmented assignment doesn't work with multiple LHS

var x = 3
var y = 4
setvar x, y += 2
echo $x $y

## status: 2
## STDOUT:
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

const x = 'foo'
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

#### var x, y = 1, 2 is NOT allowed

# The syntax consistent with JavaScript would be
# var x = 1, y = 2;

var x, y = 1, 2

## status: 2
## STDOUT:
## END


#### setvar x, y = 1, 2

# Python doesn't allow you to have annotation on each variable!
# https://www.python.org/dev/peps/pep-0526/#where-annotations-aren-t-allowed
var x Int = 3
var y Int = 4
echo "x=$x y=$y"

setvar x, y = 1, 9
echo "x=$x y=$y"

setvar y, x = x, y
echo "x=$x y=$y"

setvar x, y = x*2, x*3
echo "x=$x y=$y"

## STDOUT:
x=3 y=4
x=1 y=9
x=9 y=1
x=18 y=27
## END

#### setvar to swap List and Dict elements
var x = [1, 2, 3]
echo @x

setvar x[0], x[1] = x[1], x[0]

echo @x

var d = {int: 42}

setvar x[0], d.int = d.int, x[0]

echo @x
json write (d)

## STDOUT:
1 2 3
2 1 3
42 1 3
{
  "int": 2
}
## END

#### setvar d.key = 42 (setitem)
shopt -s oil:all

var d = {}
setvar d['f2'] = 42
setvar d.f3 = 43

# Use the opposite thing to retrieve
var f3 = d['f3']
var f2 = d.f2
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
  const x = 2
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
proc p (s, out Ref) {
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
proc q(s, out Ref) {
  echo "q s=$s"
  setref out = 'YY'
}
proc p(out Ref) {
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

#### circular dict - TODO 2023-06 REGRESS
var d = {name: 'foo'}
= d
setvar d['name'] = 123
= d
setvar d['name'] = 'mystr'
= d
#setvar d['name'] = d
#= d

# This used to print ...

## STDOUT:
(OrderedDict)   <'name': 'foo'>
(OrderedDict)   <'name': 123>
(OrderedDict)   <'name': 'mystr'>
(OrderedDict)   <'name': ...>
## END

#### circular list - TODO 2023-06 REGRESS
var L = [1,2,3]
= L
#setvar L[0] = L
#= L
## STDOUT:
(List)   [1, 2, 3]
(List)   [[...], 2, 3]
## END


#### exit code of var, const, setvar with command sub

# NOTE: This feels PROBLEMATIC without command_sub_errexit feels like it should
# be the last one ...

run() {
  $REPO_ROOT/bin/osh -O parse_proc -c "$@"

  # Identical
  # $SH +O oil:all -O parse_proc -c "$@"
}

set +o errexit

run '
var x = $(false)
echo inside1=$?
'
echo outside1=$?

run '
setvar x = $(false)
echo inside2=$?
'
echo outside2=$?

# Argument list
run '
_ split( $(false) )
echo inside3=$?
'
echo outside3=$?

# Place expression
run '
var d = {}
setvar d[ $(false) ] = 42
echo inside4=$?
'
echo outside4=$?

## STDOUT:
outside1=1
outside2=1
outside3=1
outside4=1
## END

#### setvar obj[INVALID TYPE] =

set +o errexit

$SH -c '
var d = {}
setvar d["key"] = 5
echo "d.key = $[d.key]"
setvar d[42] = 6
echo "should not get here"
'
echo outside1=$?

$SH -c '
var L = [42]
setvar L[0] = 43
echo "L[0] = $[L[0]]"
setvar L["key"] = 44
'
echo outside2=$?

## STDOUT:
d.key = 5
outside1=3
L[0] = 43
outside2=3
## END

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

#### setvar x, y = 1, 2
setvar x, y = 1, 2
echo $x $y
## STDOUT:
1 2
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

#### command sub $(echo hi)
var x = $(echo hi)
var y = $(echo '')
# Make sure we can operate on these values
echo x=${x:-default} y=${y:-default}
## STDOUT:
x=hi y=default
## END

#### shell array @(a 'b c')
shopt -s parse_at
var x = @(a 'b c')
var empty = @()
argv.py / @x @empty /

## STDOUT:
['/', 'a', 'b c', '/']
## END

#### empty array and simple_word_eval (regression test)
shopt -s parse_at simple_word_eval
var empty = @()
echo len=${#empty[@]}
argv.py / @empty /

## STDOUT:
len=0
['/', '/']
## END

#### Empty array and assignment builtin (regression)
# Bug happens with shell arrays too
empty=()
declare z=1 "${empty[@]}"
echo z=$z
## STDOUT:
z=1
## END

#### Shell arrays support tilde detection, static globbing, brace detection
shopt -s parse_at simple_word_eval
touch {foo,bar}.py
HOME=/home/bob
no_dynamic_glob='*.py'

var x = @(~/src *.py {andy,bob}@example.com $no_dynamic_glob)
argv.py @x
## STDOUT:
['/home/bob/src', 'bar.py', 'foo.py', 'andy@example.com', 'bob@example.com', '*.py']
## END

#### augmented assignment doesn't work on shell arrays
shopt -s parse_at simple_word_eval
var x = @(a 'b c')
argv.py @x

setvar x += @(d e)  # fatal error
argv.py @x
## status: 1
## STDOUT:
['a', 'b c']
## END

#### Splice in a Python list (i.e. Oil Obj var in word evaluator)
shopt -s parse_at simple_word_eval
var mylist = ["one", "two"]
argv.py @mylist
## STDOUT:
['one', 'two']
## END

#### Can't splice undefined
shopt -s all:oil
argv.py @undefined
echo done
## status: 1
## stdout-json: ""

#### Set $HOME using 'var' (i.e. Oil string var in word evaluator)
var HOME = "foo"
echo $HOME
echo ~
## STDOUT:
foo
foo
## END

#### Use shell var in Oil expression
x='abc'
var length = len(x)  # length in BYTES, unlike ${#x}
echo $length
## STDOUT:
3
## END

#### Length in two different contexts
x=(a b c)
x[10]=A
x[20]=B

# shell style: length is 5
echo shell=${#x[@]}

# Oil function call: length is 20.  I think that makes sense?  It's just a
# different notion of length.
echo oil=$len(x)

## STDOUT:
shell=5
oil=21
## END

#### $len(x) inside strings
var s = "abc"
echo -$len(s)-

# This already has a meaning ...
#echo "-$len(x)-"
#echo "-${len}(x)-"

## STDOUT:
-3-
## END

#### Func with multiple args in multiple contexts
var x = max(1+2, 3+4)
echo $x $max(1+2, 3+4)

## STDOUT:
7 7
## END


#### Trailing Comma in Param list
var x = max(1+2, 3+4,)
echo $x $max(1+2, 3+4,)

## STDOUT:
7 7
## END

#### @split(x) 
shopt -s all:oil
setvar IFS = ":"
var x = "one:two:three"
argv.py @split(x)
## STDOUT:
['one', 'two', 'three']
## END

#### @range()
shopt -s all:oil
echo @range(10, 15, 2)
## STDOUT:
10
12
14
## END

#### Wrong sigil $range() shows representation of iterator?
shopt -s all:oil
echo $range(10, 15, 2)
## STDOUT:
TODO
## END

#### Wrong sigil @max(3, 4)
shopt -s all:oil
echo @max(3, 4)
## STDOUT:
TODO
## END


#### nested expr contexts
var s = "123"

# lex_mode_e.ShCommand -> Expr -> ShCommand -> Expr
var x = $(echo 'len\n' $len(s))
echo $x
## STDOUT:
len
3
## END


# TODO:
# - test keyword args
# - test splatting *args, **kwargs
# - Multiline parsing
#
# var x = max(
#   1+2,
#   3+4,
# )
# echo $x $max(
#   1+2,
#   3+4,
# )

#### Test value.Obj inside shell arithmetic
var w = "3"
echo lt=$(( w < 4 ))
echo gt=$(( w > 4 ))

var z = 3
echo lt=$(( z < 4 ))
echo gt=$(( z > 4 ))
## STDOUT:
lt=1
gt=0
lt=1
gt=0
## END

#### Parse { setvar x = 1 }
shopt -s all:oil
var x = 1
f() { setvar x = 2 }
f
echo x=$x
## STDOUT:
x=2
## END

#### double quoted
var foo = "bar"
var x = "-$foo-${foo}-${undef:-default}-"
echo $x
## STDOUT:
-bar-bar-default-
## END

#### double quoted respects strict_array
shopt -s all:oil
var a = @(one two three)
var x = "-${a[@]}-"
echo $x
## status: 1
## stdout-json: ""

#### single quoted
var x = 'foo bar'
echo $x
setvar x = '\t\n'  # This is raw
echo $x
## STDOUT:
foo bar
\t\n
## END

#### single quoted c'foo\n
var x = c'foo\nbar'
echo "$x"
## STDOUT:
foo
bar
## END

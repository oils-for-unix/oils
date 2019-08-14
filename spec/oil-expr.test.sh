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

#### command sub $(echo hi)
var x = $(echo hi)
var y = $(echo '')
# Make sure we can operate on these values
echo x=${x:-default} y=${y:-default}
## STDOUT:
x=hi y=default
## END

#### shell array @(a 'b c')
shopt -s parse-at
var x = @(a 'b c')
var empty = @()
argv.py / @x @empty /

## STDOUT:
['/', 'a', 'b c', '/']
## END

#### empty array and simple-word-eval (regression test)
shopt -s parse-at simple-word-eval
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
shopt -s parse-at simple-word-eval
touch {foo,bar}.py
HOME=/home/bob
no_dynamic_glob='*.py'

var x = @(~/src *.py {andy,bob}@example.com $no_dynamic_glob)
argv.py @x
## STDOUT:
['/home/bob/src', 'bar.py', 'foo.py', 'andy@example.com', 'bob@example.com', '*.py']
## END

#### augmented assignment doesn't work on shell arrays
shopt -s parse-at simple-word-eval
var x = @(a 'b c')
argv.py @x

setvar x += @(d e)  # fatal error
argv.py @x
## status: 1
## STDOUT:
['a', 'b c']
## END

#### Splice in a Python list (i.e. Oil Obj var in word evaluator)
shopt -s parse-at simple-word-eval
var mylist = ["one", "two"]
argv.py @mylist
## STDOUT:
['one', 'two']
## END

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
echo oil= $len(x)

## STDOUT:
shell=5
oil=20
## END

#### @split(x) 
var IFS = ':'
var x = "one:two:three"
argv.py @split(x)
## STDOUT:
['one', 'two', 'three']
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

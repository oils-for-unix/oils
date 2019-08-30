# Oil builtins

#### push onto a=(1 2)
shopt -s parse_at
a=(1 2)
push :a '3 4' '5'
argv.py @a
## STDOUT:
['1', '2', '3 4', '5']
## END

#### push onto var a = @(1 2)
shopt -s parse_at
var a = @(1 2)
push a '3 4' '5'  # : is optional
argv.py @a
## STDOUT:
['1', '2', '3 4', '5']
## END

#### push with invalid type
s=''
push :s a b
echo status=$?
## stdout: status=1

#### push with invalid var name
push - a b
echo status=$?
## stdout: status=2

#### echo -sep, -end, -n, varying flag syntax
shopt -s all:oil
var a = @('a b' 'c d')
echo @a
echo .
echo -- @a
echo .

echo -sep '' -end '' @a; echo
echo .

echo -sep '_' -- @a
echo -sep '_' -end $' END\n' -- @a

# with =
echo -sep='_' -end=$' END\n' -- @a
# long flags
echo --sep '_' --end $' END\n' -- @a
# long flags with =
echo --sep='_' --end=$' END\n' -- @a

echo -n x
echo -n y
echo

## STDOUT:
a b
c d
.
a b
c d
.
a bc d
.
a b_c d
a b_c d END
a b_c d END
a b_c d END
a b_c d END
xy
## END

#### echo -e not supported
shopt -s all:oil
echo -e foo
echo status=$?
## stdout-json: ""
## status: 2

#### echo syntax error
shopt -s all:oil
echo ---end foo
echo status=$?
## stdout-json: ""
## status: 2

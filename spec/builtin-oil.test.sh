# Oil builtins

#### push onto a=(1 2)
shopt -s parse-at
a=(1 2)
push a _ '3 4' '5'
argv.py @a
## STDOUT:
['1', '2', '3 4', '5']
## END

#### push onto var a = @(1 2)
shopt -s parse-at
var a = @(1 2)
push a _ '3 4' '5'
argv.py @a
## STDOUT:
['1', '2', '3 4', '5']
## END

#### echo
shopt -s all:oil
var a = @('a b' 'c d')
echo @a
echo -- @a

echo -sep '_' -- @a
echo -sep '_' -end $' END\n' -- @a

# long flags
echo --sep '_' --end $' END\n' -- @a

echo -n x
echo -n y
echo
## STDOUT:
a bc d
a bc d
a b_c d
a b_c d END
a b_c d END
xy
## END

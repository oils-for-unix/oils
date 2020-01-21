# Oil builtins

#### repr
x=42
repr x
echo status=$?
repr nonexistent
echo status=$?
## STDOUT:
x = (cell val:(value.Str s:42) exported:F readonly:F)
status=0
status=1
## END

#### repr on indexed array with hole
declare -a array
array[3]=42
repr array
## STDOUT:
array = (cell val:(value.MaybeStrArray strs:[_ _ _ 42]) exported:F readonly:F)
## END


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

#### write -sep, -end, -n, varying flag syntax
shopt -s oil:all
var a = @('a b' 'c d')
write @a
write .
write -- @a
write .

write -sep '' -end '' @a; write
write .

write -sep '_' -- @a
write -sep '_' -end $' END\n' -- @a

# with =
write -sep='_' -end=$' END\n' -- @a
# long flags
write --sep '_' --end $' END\n' -- @a
# long flags with =
write --sep='_' --end=$' END\n' -- @a

write -n x
write -n y
write

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

#### write  -e not supported
shopt -s oil:all
write -e foo
write status=$?
## stdout-json: ""
## status: 2

#### write syntax error
shopt -s oil:all
write ---end foo
write status=$?
## stdout-json: ""
## status: 2

#### write --
shopt -s oil:all
write --
# This is annoying
write -- --
write done

# this is a syntax error!  Doh.
write ---
## status: 2
## STDOUT:

--
done
## END

# Oil builtins

#### repr
x=42

repr x
echo status=$?

repr -- :x
echo status=$?

repr nonexistent
echo status=$?
## STDOUT:
x = (cell exported:F readonly:F nameref:F val:(value.Str s:42))
status=0
x = (cell exported:F readonly:F nameref:F val:(value.Str s:42))
status=0
status=1
## END

#### repr on indexed array with hole
declare -a array
array[3]=42
repr array
## STDOUT:
array = (cell exported:F readonly:F nameref:F val:(value.MaybeStrArray strs:[_ _ _ 42]))
## END


#### push onto a=(1 2)
shopt -s parse_at
a=(1 2)
push :a '3 4' '5'
argv.py @a
push -- :a 6
argv.py @a
## STDOUT:
['1', '2', '3 4', '5']
['1', '2', '3 4', '5', '6']
## END

#### push onto var a = %(1 2)
shopt -s parse_at
var a = %(1 2)
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
var a = %('a b' 'c d')
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

#### write --qsn
write --qsn foo bar
write __

write --qsn 'abc def' ' 123 456'
write __

write --qsn $'one\ttwo\n'

write __
write --qsn $'\u{3bc}'


## STDOUT:
foo
bar
__
'abc def'
' 123 456'
__
'one\ttwo\n'
__
'μ'
## END


#### write --qsn --unicode
write --qsn $'\u{3bc}'
write --qsn --unicode u $'\u{3bc}'
write --qsn --unicode x $'\u{3bc}'

## STDOUT:
'μ'
'\u{3bc}'
'\xce\xbc'
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

#### read flag usage
read --lin
echo status=$?

read --line :var extra
echo status=$?
## STDOUT:
status=2
status=2
## END

#### read --line --with-eol
shopt -s oil:basic

# Hm this preserves the newline?
seq 3 | while read --line {
  write line=$_line  # implisict
}
write a b | while read --line --with-eol :myline {
  write -end '' line=$myline
}
## STDOUT:
line=1
line=2
line=3
line=a
line=b
## END

#### read --line --qsn
read --line --qsn <<EOF
'foo\n'
EOF
write --qsn -- "$_line"

## STDOUT:
'foo\n'
## END

#### read --qsn usage
read --qsn << EOF
foo
EOF
echo status=$?

## STDOUT:
status=2
## END

#### read --all
echo foo | read --all
echo "[$_all]"

echo bad > tmp.txt
read --all :x < tmp.txt
echo "[$x]"

## STDOUT:
[foo
]
[bad
]
## END


#### shopt supports long flags
shopt -p nullglob

shopt --set nullglob
shopt -p nullglob

shopt --unset nullglob
shopt -p nullglob
## STDOUT:
shopt -u nullglob
shopt -s nullglob
shopt -u nullglob
## END

#### shopt supports 'set' options
shopt -p errexit

shopt --set errexit
false

echo should not get here
## status: 1
## STDOUT:
shopt -u errexit
## END


#### shopt and block
shopt --set oil:all

echo one

shopt --unset errexit {
  echo two
  false
  echo three
}

false
echo 'should not get here'

## status: 1
## STDOUT:
one
two
three
## END

#### shopt and block status
shopt --set oil:all

shopt --unset errexit {
  false
}
# this is still 0, even though last command was 1
echo status=$?

## STDOUT:
status=0
## END

#### shopt usage error
shopt --set oil:all

echo one
shopt --set a {
  echo two
}
echo status=$?
## status: 2
## STDOUT:
one
## END

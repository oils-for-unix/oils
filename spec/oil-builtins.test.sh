# Oil builtins

#### append onto a=(1 2)
shopt -s parse_at
a=(1 2)
append :a '3 4' '5'
argv.py @a
append -- :a 6
argv.py @a
## STDOUT:
['1', '2', '3 4', '5']
['1', '2', '3 4', '5', '6']
## END

#### append onto var a = %(1 2)
shopt -s parse_at
var a = %(1 2)
append a '3 4' '5'  # : is optional
argv.py @a
## STDOUT:
['1', '2', '3 4', '5']
## END

#### append with invalid type
s=''
append :s a b
echo status=$?
## stdout: status=1

#### append with invalid var name
append - a b
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

#### read :x :y is allowed
echo 'foo bar' | read :x :y
echo x=$x y=$y

proc p {
  # If these aren't here, it will LEAK because 'read' uses DYNAMIC SCOPE.
  # TODO: Change semantics of : to be enforce that a local exists too?
  var x = ''
  var y = ''
  echo 'spam eggs' | read x :y  # OPTIONAL
  echo x=$x y=$y
}
p

echo x=$x y=$y

## STDOUT:
x=foo y=bar
x=spam y=eggs
x=foo y=bar
## END

#### Idiom for returning 'read'
proc p(:out) {
  #var tmp = ''

  # We can't do read :out in Oil.  I think that's OK -- there's consistency in
  # using setref everywhere.
  echo foo | read :tmp
  setref out = tmp
}
p :z
echo z=$z
## STDOUT:
z=foo
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

read --line --qsn <<EOF
'foo\tbar hex=\x01 mu=\u{3bc}'
EOF
write --qsn --unicode u -- "$_line"

## STDOUT:
'foo\n'
'foo\tbar hex=\u{1} mu=\u{3bc}'
## END

#### read --line --with-eol --qsn

# whitespace is allowed after closing single quote; it doesn't make a 
# difference.

read --line --with-eol --qsn <<EOF
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

#### read --all-lines
seq 3 | read --all-lines :nums
write --sep ' ' -- @nums
## STDOUT:
1 2 3
## END

#### read --all-lines --with-eol
seq 3 | read --all-lines --with-eol :nums
write --sep '' -- @nums
## STDOUT:
1
2
3
## END

#### read --all-lines --qsn --with-eol
read --all-lines --qsn --with-eol :lines << EOF
foo
bar
'one\ntwo'
EOF
write --sep '' -- @lines
## STDOUT:
foo
bar
one
two
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

#### read -0 is like read -r -d ''
set -o errexit

mkdir -p read0
cd read0
touch a\\b\\c\\d

find . -type f -a -print0 | read -r -d '' name
echo "[$name]"

find . -type f -a -print0 | read -0
echo "[$REPLY]"

## STDOUT:
[./a\b\c\d]
[./a\b\c\d]
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

#### shopt --print

# TODO: It would be nice to print long flags ...

shopt -p errexit
shopt -p nullglob

echo --
shopt -p strict:all | head -n 3

echo --
shopt --set strict:all
shopt -p strict:all | head -n 3

## STDOUT:
shopt -u errexit
shopt -u nullglob
--
shopt -u errexit
shopt -u inherit_errexit
shopt -u nounset
--
shopt -s errexit
shopt -s inherit_errexit
shopt -s nounset
## END

#### simple_test_builtin

test -n "foo"
echo status=$?

test -n "foo" -a -n "bar"
echo status=$?

[ -n foo ]
echo status=$?

shopt --set oil:all
shopt --unset errexit

test -n "foo" -a -n "bar"
echo status=$?

[ -n foo ]
echo status=$?

test -z foo
echo status=$?

## STDOUT:
status=0
status=0
status=0
status=2
status=2
status=1
## END

#### long flags to test
# no options necessary!

test --dir /
echo status=$?

touch foo
test --file foo
echo status=$?

test --exists /
echo status=$?

test --symlink foo
echo status=$?

test --typo foo
echo status=$?

## STDOUT:
status=0
status=0
status=0
status=1
status=2
## END


#### push-registers
shopt --set oil:basic
shopt --unset errexit

status_code() {
  return $1
}

[[ foo =~ (.*) ]]

status_code 42
push-registers {
  status_code 43
  echo status=$?

  [[ bar =~ (.*) ]]
  echo ${BASH_REMATCH[@]}
}
echo status=$?  # push-registers will return 42

echo ${BASH_REMATCH[@]}
## STDOUT:
status=43
bar bar
status=42
foo foo
## END

#### module
module main || return
source $REPO_ROOT/spec/testdata/module/common.oil
source $REPO_ROOT/spec/testdata/module/module1.oil
## STDOUT:
common
module1
## END


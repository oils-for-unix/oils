
## oils_failures_allowed: 6

#### append onto BashArray a=(1 2)
shopt -s parse_at
a=(1 2)
append '3 4' '5' (a)
argv.py "${a[@]}"

append -- 6 (a)
argv.py "${a[@]}"

## STDOUT:
['1', '2', '3 4', '5']
['1', '2', '3 4', '5', '6']
## END

#### append onto var a = :| 1 2 |
shopt -s parse_at parse_proc
var a = :| 1 2 |
append '3 4' '5' (a)
argv.py @a
## STDOUT:
['1', '2', '3 4', '5']
## END

#### append onto var a = ['1', '2']
shopt -s parse_at parse_proc
var a = ['1', '2']
append '3 4' '5' (a)
argv.py @a
## STDOUT:
['1', '2', '3 4', '5']
## END

#### append without typed arg
append a b
## status: 2

#### append passed invalid type
s=''
append a b (s)
echo status=$?
## status: 3

#### write --sep, --end, -n, varying flag syntax
shopt -s ysh:all
var a = %('a b' 'c d')
write @a
write .
write -- @a
write .

write --sep '' --end '' @a; write
write .

write --sep '_' -- @a
write --sep '_' --end $' END\n' -- @a

# with =
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
xy
## END

#### write --qsn
write --qsn foo bar
write __

write --qsn 'abc def' ' 123 456'
write __

write --qsn $'one\ttwo\n'


## STDOUT:
foo
bar
__
'abc def'
' 123 456'
__
'one\ttwo\n'
## END

#### write --j8

write --j8 j"\u{3bc}"

## STDOUT:
'μ'
## END

#### write --j8 --unicode

write --j8 $'\u{3bc}'
write --j8 --unicode u $'\u{3bc}'
write --j8 --unicode x $'\u{3bc}'

## STDOUT:
'μ'
'\u{3bc}'
'\xce\xbc'
## END

#### write  -e not supported
shopt -s ysh:all
write -e foo
write status=$?
## stdout-json: ""
## status: 2

#### write syntax error
shopt -s ysh:all
write ---end foo
write status=$?
## stdout-json: ""
## status: 2

#### write --
shopt -s ysh:all
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
shopt --set parse_proc

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

#### read (&x) is usage error

var x = null  # allow no initialization
echo hello | read (&x)
echo status=$?

## STDOUT:
status=2
## END

#### read --line --with-eol
shopt -s ysh:upgrade

# Hm this preserves the newline?
seq 3 | while read --line {
  write reply=$_reply # implicit
}
write a b | while read --line --with-eol (&myline) {
  write --end '' myline=$myline
}
## STDOUT:
reply=1
reply=2
reply=3
myline=a
myline=b
## END

#### read --line --qsn
read --line --qsn <<EOF
'foo\n'
EOF
write --qsn -- "$_reply"

read --line --qsn <<EOF
'foo\tbar hex=\x01 mu=\u{3bc}'
EOF
write --qsn --unicode u -- "$_reply"

echo '$' | read --line --qsn
write --qsn -- "$_reply"

## STDOUT:
'foo\n'
'foo\tbar hex=\u{1} mu=\u{3bc}'
'$'
## END

#### read --line --qsn accepts optional $''

# PROBLEM: is it limited to $'  ?  What about $3.99 ?
# I think you just check for those 2 chars

echo $'$\'foo\'' | read --line --qsn
write -- "$_reply"
## STDOUT:
foo
## END

#### read --line --with-eol --qsn

# whitespace is allowed after closing single quote; it doesn't make a 
# difference.

read --line --with-eol --qsn <<EOF
'foo\n'
EOF
write --qsn -- "$_reply"
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
echo "[$_reply]"

echo bad > tmp.txt
read --all (&x) < tmp.txt
echo "[$x]"

## STDOUT:
[foo
]
[bad
]
## END

#### read --line from directory is an error (EISDIR)
mkdir -p ./dir
read --line < ./dir
echo status=$?
## STDOUT:
status=1
## END

#### read --all from directory is an error (EISDIR)
mkdir -p ./dir
read --all < ./dir
echo status=$?
## STDOUT:
status=1
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

#### simple_test_builtin

test -n "foo"
echo status=$?

test -n "foo" -a -n "bar"
echo status=$?

[ -n foo ]
echo status=$?

shopt --set ysh:all
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
shopt --set ysh:upgrade
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
# WEIRD SEMANTIC TO REVISIT: push-registers is "SILENT" as far as exit code
# This is for the headless shell, but hasn't been tested.
# Better method: maybe we should provide a way of SETTING $?

echo status=$?

echo ${BASH_REMATCH[@]}
## STDOUT:
status=43
bar bar
status=42
foo foo
## END

#### push-registers usage
shopt --set parse_brace

push-registers
echo status=$?

push-registers a b
echo status=$?

push-registers a b {  # hm extra args are ignored
  echo hi
}
echo status=$?

## STDOUT:
status=2
status=2
hi
status=0
## END

#### fopen
shopt --set parse_brace parse_proc

proc p {
  echo 'proc'
}

fopen >out.txt {
  p
  echo 'builtin'
}

cat out.txt

echo ---

fopen <out.txt {
  tac
}

# Awkward bash syntax, but we'll live with it
fopen {left}>left.txt {right}>right.txt {
  echo 1 >& $left
  echo 1 >& $right

  echo 2 >& $left
  echo 2 >& $right

  echo 3 >& $left
}

echo ---
comm -23 left.txt right.txt

## STDOUT:
proc
builtin
---
builtin
proc
---
3
## END

#### type(x)
echo $[type(1234)]
echo $[type('foo')]
echo $[type(false)]
echo $[type(1.234)]
echo $[type([])]
echo $[type({})]
echo $[type(null)]

shopt --set ysh:upgrade

func f() {
  return (42)
}

echo $[type(f)]
echo $[type(len)]
echo $[type('foo'->startsWith)]
echo $[type('foo'=>join)]  # Type error happens later
echo $[type(1..3)]
## STDOUT:
Int
Str
Bool
Float
List
Dict
Null
Func
BuiltinFunc
BoundFunc
BoundFunc
Range
## END

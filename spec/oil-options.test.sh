# Test shell execution options.

#### simple_word_eval doesn't split, glob, or elide empty
mkdir mydir
touch foo.txt bar.txt spam.txt
spaces='a b'
dir=mydir
glob=*.txt
prefix=sp
set -- 'x y' z

for i in 1 2; do
  local empty=
  argv.py $spaces $glob $empty $prefix*.txt

  # arrays still work too, with this weird rule
  argv.py -"$@"-

  shopt -s simple_word_eval
done
## STDOUT:
['a', 'b', 'bar.txt', 'foo.txt', 'spam.txt', 'spam.txt']
['-x y', 'z-']
['a b', '*.txt', '', 'spam.txt']
['-x y', 'z-']
## END

#### simple_word_eval and strict_array conflict over globs
touch foo.txt bar.txt
set -- f

argv.py "$@"*.txt
shopt -s simple_word_eval
argv.py "$@"*.txt
shopt -s strict_array
argv.py "$@"*.txt

## status: 1
## STDOUT:
['foo.txt']
['foo.txt']
## END

#### parse_at
words=(a 'b c')
argv.py @words

# TODO: This should be parse_oil-at, and only allowed at the top of the file?
# Going midway is weird?  Then you can't bin/osh -n?

shopt -s parse_at
argv.py @words

## STDOUT:
['@words']
['a', 'b c']
## END

#### parse_at can't be used outside top level
f() {
  shopt -s parse_at
  echo status=$?
}
f
echo 'should not get here'
## status: 1
## stdout-json: ""


#### sourcing a file that sets parse_at
cat >lib.sh <<EOF
shopt -s parse_at
echo lib.sh
EOF

words=(a 'b c')
argv.py @words

# This has a side effect, which is a bit weird, but not sure how to avoid it.
# Maybe we should say that libraries aren't allowed to change it?

source lib.sh
echo 'main.sh'

argv.py @words
## STDOUT:
['@words']
lib.sh
main.sh
['a', 'b c']
## END

#### parse_at can be specified through sh -O
$SH +O parse_at -c 'words=(a "b c"); argv.py @words'
$SH -O parse_at -c 'words=(a "b c"); argv.py @words'
## STDOUT:
['@words']
['a', 'b c']
## END

#### @a splices into $0
shopt -s simple_word_eval parse_at
a=(echo hi)
"${a[@]}"
@a

# Bug fix
shopt -s strict_array

"${a[@]}"
@a
## STDOUT:
hi
hi
hi
hi
## END

#### ARGV is alias for "$@"
shopt -s parse_at
argv.py "$@"
argv.py @ARGV
argv.py "${ARGV[@]}"  # not useful, but it works!

set -- 'a b' c
argv.py "$@"
argv.py @ARGV

f() {
  argv.py "$@"
  argv.py @ARGV
}
f 1 '2 3'
## STDOUT:
[]
[]
[]
['a b', 'c']
['a b', 'c']
['1', '2 3']
['1', '2 3']
## END

#### shopt -s strict:all
shopt -s strict:all
# normal option names
shopt -o -p | grep -- ' -o ' | grep -v hashall
shopt -p | grep -- ' -s '
## STDOUT:
set -o errexit
set -o nounset
set -o pipefail
shopt -s nullglob
shopt -s inherit_errexit
shopt -s strict_argv
shopt -s strict_arith
shopt -s strict_array
shopt -s strict_control_flow
shopt -s strict_errexit
shopt -s strict_eval_builtin
shopt -s strict_word_eval
shopt -s strict_backslash
shopt -s strict_glob
## END

#### shopt -s oil:basic
shopt -s oil:basic
# normal option names
shopt -o -p | grep -- ' -o ' | grep -v hashall
shopt -p | grep -- ' -s '
## STDOUT:
set -o errexit
set -o nounset
set -o pipefail
shopt -s inherit_errexit
shopt -s strict_argv
shopt -s strict_arith
shopt -s strict_array
shopt -s strict_control_flow
shopt -s strict_errexit
shopt -s strict_eval_builtin
shopt -s strict_word_eval
shopt -s strict_backslash
shopt -s strict_glob
shopt -s simple_word_eval
shopt -s more_errexit
shopt -s simple_test_builtin
shopt -s parse_at
shopt -s parse_brace
shopt -s parse_index_expr
shopt -s parse_paren
shopt -s parse_rawc
## END

#### osh -O oil:basic 
$SH -O oil:basic -c 'var x = @(one two three); echo @x'
## STDOUT:
one two three
## END

#### strict:all includes inherit_errexit
shopt -s strict:all
echo $(echo one; false; echo two)
## STDOUT:
one
## END

#### parse_set
x=init

set x=42
echo x=$x
echo argv "$@"

shopt -s parse_set
set x=42
builtin set --
echo x=$x
echo argv "$@"

## STDOUT:
x=init
argv x=42
x=42
argv
## END

#### parse_brace: bad block to assignment builtin
shopt -s oil:basic
# This is a fatal programming error.  It's unlike passing an extra arg?
local x=y { echo 'bad block' }
echo status=$?
## status: 1
## stdout-json: ""

#### parse_brace: bad block to external program
shopt -s oil:basic
# This is a fatal programming error.  It's unlike passing an extra arg?
ls { echo 'bad block' }
echo status=$?
## status: 1
## stdout-json: ""

#### parse_brace: cd { } in pipeline
shopt -s oil:basic
cd /tmp {
  pwd
  pwd
} | tr a-z A-Z
## STDOUT:
/TMP
/TMP
## END


#### parse_brace: if accepts blocks
shopt -s oil:basic
if test -n foo {
  echo one
}
# harder
if test -n foo; test -n bar {
  echo two
}

# just like POSIX shell!
if test -n foo;

   test -n bar {
  echo three
}

if test -z foo {
  echo if
} else {
  echo else
}

if test -z foo {
  echo if
} elif test -z '' {
  echo elif
} else {
  echo else
}

echo 'one line'
if test -z foo { echo if } elif test -z '' { echo 1 }; if test -n foo { echo 2 };

echo 'sh syntax'
if test -z foo; then echo if; elif test -z ''; then echo 1; fi; if test -n foo { echo 2 };

# NOTE: This is not alowed because it's like a brace group!
# if test -n foo; { 

## STDOUT:
one
two
three
else
elif
one line
1
2
sh syntax
1
2
## END

#### parse_brace: brace group in if condition

# strict_errexit would make this a RUNTIME error
shopt -s parse_brace
if { echo one; echo two } {
  echo three
}
## STDOUT:
one
two
three
## END

#### parse_brace: while/until
shopt -s oil:basic
while true {
  echo one
  break
}
while true { echo two; break }

echo 'sh syntax'
while true; do echo three; break; done
## STDOUT:
one
two
sh syntax
three
## END

#### parse_brace: for-in loop
shopt -s oil:basic
for x in one two {
  echo $x
}
for x in three { echo $x }

echo 'sh syntax'
for x in four; do echo $x; done

## STDOUT:
one
two
three
sh syntax
four
## END

#### parse_brace case
shopt -s oil:basic

var files = @(foo.py 'foo test.sh')
for name in "${files[@]}" ; do
  case $name in
    *.py)
      echo python
      ;;
    *.sh)
      echo shell
      ;;
  esac
done

for name in @files {
  case $name {
  (*.py)
    echo python
    ;;
  (*.sh) echo shell ;;
  }
}

## STDOUT:
python
shell
python
shell
## END

#### parse_paren: if statement
shopt -s oil:basic
var x = 1
if (x < 42) {
  echo less
}

if (x < 0) {
  echo negative
} elif (x < 42) {
  echo less
}

if (x < 0) {
  echo negative
} elif (x < 1) {
  echo less
} else {
  echo other
}


## STDOUT:
less
less
other
## END

#### parse_paren: while statement
shopt -s oil:basic

# ksh style
var x = 1
while (( x < 3 )) {
  echo $x
  setvar x += 1
}
echo 'done ksh'

# sh style
var y = 1
while test $y -lt 3 {
  echo $y
  setvar y += 1
}
echo 'done sh'

# oil
var z = 1
while (z < 3) {
  echo $z
  setvar z += 1
}
echo 'done oil'

## STDOUT:
1
2
done ksh
1
2
done sh
1
2
done oil
## END

#### while subshell without parse_paren
while ( echo one ); do
  echo two
  break
done
## STDOUT:
one
two
## END

#### parse_paren: for loop
shopt -s oil:basic
var array = @(one two three)
for (item in array) {
  echo $item
}

echo ---

declare -A A=([k]=v [k2]=v2)  # iterate over keys
for (key in A) {
  echo $key
} | sort
## STDOUT:
one
two
three
---
k
k2
## END

#### parse_equals: allows bare assignment
shopt -s oil:all  # including nice options
x = 1 + 2*3
echo $x
## STDOUT:
7
## END

#### parse_equals: disallows ENV=val mycommand
shopt -s oil:all
ENV=val echo hi
## status: 2
## stdout-json: ""

#### parse_equals: disallows var=val
shopt -s oil:all
var=val
## status: 2
## stdout-json: ""

#### parse_rawc: C strings in @() array literals
shopt -s oil:basic

# BUG: Surprising that this doesn't work because of command mode!
var lines=@(c'aa\tbb' c'cc\tdd')
echo @lines

## STDOUT:
## END


#### do f(x)
shopt -s parse_do
func f(x) {
  echo foo $x
}
do f(42)
## STDOUT:
foo 42
## END

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

#### shopt -s all:strict
shopt -s all:strict
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

#### shopt -s all:oil
shopt -s all:oil
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
shopt -s simple_echo
shopt -s parse_at
shopt -s parse_brace
shopt -s parse_equals
shopt -s parse_paren
shopt -s parse_set
## END

#### osh -O all:oil 
$SH -O all:oil -c 'var x = @(one two three); echo @x'
## STDOUT:
one
two
three
## END

#### all:strict includes inherit_errexit
shopt -s all:strict
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

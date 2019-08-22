# Test shell execution options.

#### simple-word-eval doesn't split, glob, or elide empty
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

  shopt -s simple-word-eval
done
## STDOUT:
['a', 'b', 'bar.txt', 'foo.txt', 'spam.txt', 'spam.txt']
['-x y', 'z-']
['a b', '*.txt', '', 'spam.txt']
['-x y', 'z-']
## END

#### simple-word-eval and strict-array conflict over globs
touch foo.txt bar.txt
set -- f

argv.py "$@"*.txt
shopt -s simple-word-eval
argv.py "$@"*.txt
shopt -s strict-array
argv.py "$@"*.txt

## status: 1
## STDOUT:
['foo.txt']
['foo.txt']
## END

#### parse-at
words=(a 'b c')
argv.py @words

# TODO: This should be parse-oil-at, and only allowed at the top of the file?
# Going midway is weird?  Then you can't bin/osh -n?

shopt -s parse-at
argv.py @words

## STDOUT:
['@words']
['a', 'b c']
## END

#### parse-at can't be used outside top level
f() {
  shopt -s parse-at
  echo status=$?
}
f
echo 'should not get here'
## status: 1
## stdout-json: ""


#### sourcing a file that sets parse-at
cat >lib.sh <<EOF
shopt -s parse-at
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

#### parse-at can be specified through sh -O
$SH +O parse-at -c 'words=(a "b c"); argv.py @words'
$SH -O parse-at -c 'words=(a "b c"); argv.py @words'
## STDOUT:
['@words']
['a', 'b c']
## END

#### @a splices into $0
shopt -s simple-word-eval parse-at
a=(echo hi)
"${a[@]}"
@a

# Bug fix
shopt -s strict-array

"${a[@]}"
@a
## STDOUT:
hi
hi
hi
hi
## END

#### ARGV is alias for "$@"
shopt -s parse-at
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

#### shopt -s all:oil
shopt -s all:oil
# normal option names
shopt -o -p | grep -- ' -o ' | grep -v hashall
shopt -p | grep -- ' -s '
## STDOUT:
set -o errexit
set -o nounset
set -o pipefail
shopt -s strict-argv
shopt -s strict-arith
shopt -s strict-array
shopt -s strict-control-flow
shopt -s strict-eval-builtin
shopt -s strict-word-eval
shopt -s strict-backslash
shopt -s strict-glob
shopt -s simple-word-eval
shopt -s parse-at
shopt -s parse-brace
shopt -s parse-equals
shopt -s parse-paren
shopt -s parse-set
## END

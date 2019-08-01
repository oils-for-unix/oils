#!/bin/bash
#
# Usage:
#   ./oil-options.test.sh <function name>

#### static-word-eval doesn't split, glob, or elide empty
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

  shopt -s static-word-eval
done
## STDOUT:
['a', 'b', 'bar.txt', 'foo.txt', 'spam.txt', 'spam.txt']
['-x y', 'z-']
['a b', '*.txt', '', 'spam.txt']
['-x y', 'z-']
## END

#### static-word-eval and strict-array conflict over globs
touch foo.txt bar.txt
set -- f

argv.py "$@"*.txt
shopt -s static-word-eval
argv.py "$@"*.txt
shopt -s strict-array
argv.py "$@"*.txt

## status: 1
## STDOUT:
['foo.txt']
['foo.txt']
## END

#### oil-at
words=(a 'b c')
argv.py @words

# TODO: This should be parse-oil-at, and only allowed at the top of the file?
# Going midway is weird?  Then you can't bin/osh -n?

shopt -s oil-at
argv.py @words

## STDOUT:
['@words']
['a', 'b c']
## END

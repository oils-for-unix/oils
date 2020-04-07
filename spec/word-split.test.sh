#!/usr/bin/env bash

# NOTE on bash bug:  After setting IFS to array, it never splits anymore?  Even
# if you assign IFS again.

#### IFS is scoped
IFS=b
word=abcd
f() { local IFS=c; argv.py $word; }
f
argv.py $word
## stdout-json: "['ab', 'd']\n['a', 'cd']\n"

#### Tilde sub is not split, but var sub is
HOME="foo bar"
argv.py ~
argv.py $HOME
## stdout-json: "['foo bar']\n['foo', 'bar']\n"

#### Word splitting
a="1 2"
b="3 4"
argv.py $a"$b"
## stdout-json: "['1', '23 4']\n"

#### Word splitting 2
a="1 2"
b="3 4"
c="5 6"
d="7 8"
argv.py $a"$b"$c"$d"
## stdout-json: "['1', '23 45', '67 8']\n"

# Has tests on differences between  $*  "$*"  $@  "$@"
# http://stackoverflow.com/questions/448407/bash-script-to-receive-and-repass-quoted-parameters

#### $*
fun() { argv.py -$*-; }
fun "a 1" "b 2" "c 3"
## stdout: ['-a', '1', 'b', '2', 'c', '3-']

#### "$*"
fun() { argv.py "-$*-"; }
fun "a 1" "b 2" "c 3"
## stdout: ['-a 1 b 2 c 3-']

#### $@
# How does this differ from $* ?  I don't think it does.
fun() { argv.py -$@-; }
fun "a 1" "b 2" "c 3"
## stdout: ['-a', '1', 'b', '2', 'c', '3-']

#### "$@"
fun() { argv.py "-$@-"; }
fun "a 1" "b 2" "c 3"
## stdout: ['-a 1', 'b 2', 'c 3-']

#### empty argv
argv.py 1 "$@" 2 $@ 3 "$*" 4 $* 5
## stdout: ['1', '2', '3', '', '4', '5']

#### Word elision with space
s1=' '
argv.py $s1
## stdout: []

#### Word elision with non-whitespace IFS
# Treated differently than the default IFS.  What is the rule here?
IFS='_'
char='_'
space=' '
empty=''
argv.py $char
argv.py $space
argv.py $empty
## STDOUT:
['']
[' ']
[]
## END

#### Leading/trailing word elision with non-whitespace IFS
# This behavior is weird.
IFS=_
s1='_a_b_'
argv.py $s1
## stdout: ['', 'a', 'b']

#### Leading ' ' vs leading ' _ '
# This behavior is weird, but all shells agree.
IFS='_ '
s1='_ a  b _ '
s2='  a  b _ '
argv.py $s1
argv.py $s2
## STDOUT:
['', 'a', 'b']
['a', 'b']
## END

#### Multiple non-whitespace IFS chars.
IFS=_-
s1='a__b---c_d'
argv.py $s1
## stdout: ['a', '', 'b', '', '', 'c', 'd']

#### IFS with whitespace and non-whitepace.
# NOTE: Three delimiters means two empty words in the middle.  No elision.
IFS='_ '
s1='a_b _ _ _ c  _d e'
argv.py $s1
## stdout: ['a', 'b', '', '', 'c', 'd', 'e']

#### empty $@ and $* is elided
fun() { argv.py 1 $@ $* 2; }
fun
## stdout: ['1', '2']

#### unquoted empty arg is elided
empty=""
argv.py 1 $empty 2
## stdout: ['1', '2']

#### unquoted whitespace arg is elided
space=" "
argv.py 1 $space 2
## stdout: ['1', '2']

#### empty literals are not elided
space=" "
argv.py 1 $space"" 2
## stdout: ['1', '', '2']

#### no splitting when IFS is empty
IFS=""
foo="a b"
argv.py $foo
## stdout: ['a b']

#### default value can yield multiple words
argv.py 1 ${undefined:-"2 3" "4 5"} 6
## stdout: ['1', '2 3', '4 5', '6']

#### default value can yield multiple words with part joining
argv.py 1${undefined:-"2 3" "4 5"}6
## stdout: ['12 3', '4 56']

#### default value with unquoted IFS char
IFS=_
argv.py 1${undefined:-"2_3"x_x"4_5"}6
## stdout: ['12_3x', 'x4_56']

#### IFS empty doesn't do splitting
IFS=''
x=$(echo -e ' a b\tc\n')
argv.py $x
## STDOUT:
[' a b\tc']
## END
## N-I dash STDOUT:
['-e  a b\tc']
## END


#### IFS unset behaves like $' \t\n'
unset IFS
x=$(echo -e ' a b\tc\n')
argv.py $x
## STDOUT:
['a', 'b', 'c']
## END
## N-I dash STDOUT:
['-e', 'a', 'b', 'c']
## END

#### IFS='\'
# NOTE: OSH fails this because of double backslash escaping issue!
IFS='\'
s='a\b'
argv.py $s
## STDOUT:
['a', 'b']
## END

#### IFS='\ '
# NOTE: OSH fails this because of double backslash escaping issue!
# When IFS is \, then you're no longer using backslash escaping.
IFS='\ '
s='a\b \\ c d\'
argv.py $s
## STDOUT:
['a', 'b', '', 'c', 'd']
## END

#### IFS characters are glob metacharacters
IFS='* '
s='a*b c'
argv.py $s

IFS='?'
s='?x?y?z?'
argv.py $s

IFS='['
s='[x[y[z['
argv.py $s
## STDOUT:
['a', 'b', 'c']
['', 'x', 'y', 'z']
['', 'x', 'y', 'z']
## END

#### Trailing space
argv.py 'Xec  ho '
argv.py X'ec  ho '
argv.py X"ec  ho "
## STDOUT:
['Xec  ho ']
['Xec  ho ']
['Xec  ho ']
## END

#### Empty IFS (regression for bug)
IFS=
echo ["$*"]
set a b c
echo ["$*"]
## STDOUT:
[]
[abc]
## END

#### Unset IFS (regression for bug)
set a b c
unset IFS
echo ["$*"]
## STDOUT:
[a b c]
## END

#### IFS=o (regression for bug)
IFS=o
echo hi
## STDOUT:
hi
## END

#### IFS and joining arrays
IFS=:
set -- x 'y z'
argv.py "$@"
argv.py $@
argv.py "$*"
argv.py $*
## STDOUT:
['x', 'y z']
['x', 'y z']
['x:y z']
['x', 'y z']
## END

#### IFS and joining arrays by assignments
IFS=:
set -- x 'y z'

s="$@"
argv.py "$s"

s=$@
argv.py "$s"

s"$*"
argv.py "$s"

s=$*
argv.py "$s"

# bash and mksh agree, but this doesn't really make sense to me.
# In OSH, "$@" is the only real array, so that's why it behaves differently.

## STDOUT:
['x y z']
['x y z']
['x y z']
['x:y z']
## END
## OK dash STDOUT:
['x:y z']
['x:y z']
['x:y z']
['x:y z']
## END


# TODO:
# - unquoted args of whitespace are not elided (when IFS = null)
# - empty quoted args are kept
#
# - $* $@ with empty IFS
# - $* $@ with custom IFS
#
# - no splitting when IFS is empty
# - word splitting removes leading and trailing whitespace

# TODO: test framework needs common setup

# Test IFS and $@ $* on all these
#### TODO
empty=""
space=" "
AB="A B"
X="X"
Yspaces=" Y "


#### IFS='' with $@ and $*
set -- a 'b c'
IFS=''
argv.py at $@
argv.py star $*

# zsh agrees
## STDOUT:
['at', 'a', 'b c']
['star', 'a', 'b c']
## END
## BUG ash STDOUT:
['at', 'ab c']
['star', 'ab c']
## END

#### IFS='' with $@ and $* and printf
set -- a 'b c'
IFS=''
printf '[%s]\n' $@
printf '[%s]\n' $*
## STDOUT:
[a]
[b c]
[a]
[b c]
## END
## BUG ash STDOUT:
[ab c]
[ab c]
## END

#### IFS='' with ${a[@]} and ${a[*]}
myarray=(a 'b c')
IFS=''
argv.py at ${myarray[@]}
argv.py star ${myarray[*]}

## STDOUT:
['at', 'a', 'b c']
['star', 'a', 'b c']
## END
## N-I dash/ash status: 2
## N-I dash/ash stdout-json: ""

#### Bug #628 split on : with : in literal word (CRASH)
IFS=':'
word='a:'
argv.py ${word}:b
argv.py ${word}:
## STDOUT:
['a', ':b']
['a', ':']
## END

#### Bug #698, similar crash
var='\'
set -f
echo $var
## STDOUT:
\
## END

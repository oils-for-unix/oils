#!/bin/bash

# NOTE on bash bug:  After setting IFS to array, it never splits anymore?  Even
# if you assign IFS again.

### IFS is scoped
IFS=b
word=abcd
f() { local IFS=c; argv $word; }
f
argv $word
# stdout-json: "['ab', 'd']\n['a', 'cd']\n"

### Tilde sub is not split, but var sub is
HOME="foo bar"
argv ~
argv $HOME
# stdout-json: "['foo bar']\n['foo', 'bar']\n"

### Word splitting
a="1 2"
b="3 4"
argv $a"$b"
# stdout-json: "['1', '23 4']\n"

### Word splitting 2
a="1 2"
b="3 4"
c="5 6"
d="7 8"
argv $a"$b"$c"$d"
# stdout-json: "['1', '23 45', '67 8']\n"

# Has tests on differences between  $*  "$*"  $@  "$@"
# http://stackoverflow.com/questions/448407/bash-script-to-receive-and-repass-quoted-parameters

### $*
func() { argv -$*-; }
func "a 1" "b 2" "c 3"
# stdout: ['-a', '1', 'b', '2', 'c', '3-']

### "$*"
func() { argv "-$*-"; }
func "a 1" "b 2" "c 3"
# stdout: ['-a 1 b 2 c 3-']

### $@
# How does this differ from $* ?  I don't think it does.
func() { argv -$@-; }
func "a 1" "b 2" "c 3"
# stdout: ['-a', '1', 'b', '2', 'c', '3-']

### "$@"
func() { argv "-$@-"; }
func "a 1" "b 2" "c 3"
# stdout: ['-a 1', 'b 2', 'c 3-']

### empty $@ and $* is elided
func() { argv 1 $@ $* 2; }
func
# stdout: ['1', '2']

### unquoted empty arg is elided
empty=""
argv 1 $empty 2
# stdout: ['1', '2']

### unquoted whitespace arg is elided
space=" "
argv 1 $space 2
# stdout: ['1', '2']

### empty literals are not elided
space=" "
argv 1 $space"" 2
# stdout: ['1', '', '2']

### no splitting when IFS is empty
IFS=""
foo="a b"
argv $foo
# stdout: ['a b']

### default value can yield multiple words
argv 1 ${undefined:-"2 3" "4 5"} 6
# stdout: ['1', '2 3', '4 5', '6']


# TODO:
# - unquoted args of whitespace are not elided (when IFS = null)
# - empty quoted args are kept
# - Test ${@:1} and so forth?
#
# - $* $@ with empty IFS
# - $* $@ with custom IFS
#
# - no splitting when IFS is empty
# - word splitting removes leading and trailing whitespace

# TODO: test framework needs common setup

# Test IFS and $@ $* on all these
### TODO
empty=""
space=" "
AB="A B"
X="X"
Yspaces=" Y "

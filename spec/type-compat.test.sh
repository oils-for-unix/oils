#!/usr/bin/env bash
#
# Tests for bash's type flags on cells.  Hopefully we don't have to implement
# this, but it's good to know the behavior.
#
# OSH follows a Python-ish model of types carried with values/objects, not
# locations.
#
# See https://github.com/oilshell/oil/issues/26

#### declare -i
declare s
s='1 '
s+=' 2 '  # string append
declare -i i
i='1 '
i+=' 2 '  # arith add
declare -i j
j=x  # treated like zero
j+=' 2 '  # arith add
echo "$s|$i|$j"
## stdout: 1  2 |3|2

#### append in arith context
declare s
(( s='1 '))
(( s+=' 2 '))  # arith add
declare -i i
(( i='1 ' ))
(( i+=' 2 ' ))
declare -i j
(( j='x ' ))  # treated like zero
(( j+=' 2 ' ))
echo "$s|$i|$j"
## stdout: 3|3|2

#### declare array vs. string: mixing -a +a and () ''
# dynamic parsing of first argument.
declare +a 'xyz1=1'
declare +a 'xyz2=(2 3)'
declare -a 'xyz3=4'
declare -a 'xyz4=(5 6)'
argv.py "${xyz1}" "${xyz2}" "${xyz3[@]}" "${xyz4[@]}"
## stdout: ['1', '(2 3)', '4', '5', '6']

#### declare array vs. associative array
# Hm I don't understand why the array only has one element.  I guess because
# index 0 is used twice?
declare -a 'array=([a]=b [c]=d)'
declare -A 'assoc=([a]=b [c]=d)'
argv.py "${#array[@]}" "${!array[@]}" "${array[@]}"
argv.py "${#assoc[@]}" "${!assoc[@]}" "${assoc[@]}"
## stdout-json: "['1', '0', 'd']\n['2', 'a', 'c', 'b', 'd']\n"

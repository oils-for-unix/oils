#!/usr/bin/env bash

### [[ glob matching, [[ has no glob expansion
[[ foo.py == *.py ]] && echo true
[[ foo.p  == *.py ]] || echo false
# stdout-json: "true\nfalse\n"

### [[ glob matching with escapes
[[ 'foo.*' == *."*" ]] && echo true
# note that the pattern arg to fnmatch should be '*.\*'
# stdout: true

### equality
[[ '*.py' == '*.py' ]] && echo true
[[ foo.py == '*.py' ]] || echo false
# stdout-json: "true\nfalse\n"

### [[ glob matching with unquoted var
pat=*.py
[[ foo.py == $pat ]] && echo true
[[ foo.p  == $pat ]] || echo false
# stdout-json: "true\nfalse\n"

### [[ regex matching
# mksh doesn't have this syntax of regex matching.  I guess it comes from perl?
regex='.*\.py'
[[ foo.py =~ $regex ]] && echo true
[[ foo.p  =~ $regex ]] || echo false
# stdout-json: "true\nfalse\n"
# N-I mksh stdout-json: ""
# N-I mksh status: 1

### [[ regex syntax error
# hm, it doesn't show any error, but it exits 2.
[[ foo.py =~ * ]] && echo true
# status: 2
# N-I mksh status: 1

### [[ has no word splitting
var='one two'
[[ 'one two' == $var ]] && echo true
# stdout: true

### [[ has quote joining
var='one two'
[[ 'one 'tw"o" == $var ]] && echo true
# stdout: true

### [[ empty string is false
[[ 'a' ]] && echo true
[[ ''  ]] || echo false
# stdout-json: "true\nfalse\n"

### && chain
[[ t && t && '' ]] || echo false
# stdout: false

### || chain
[[ '' || '' || t ]] && echo true
# stdout: true

### [[ compound expressions
# Notes on whitespace:
# - 1 and == need space seprating them, but ! and ( don't.
# - [[ needs whitesapce after it, but ]] doesn't need whitespace before it!
[[ ''||!(1 == 2)&&(2 == 2)]] && echo true
# stdout: true

# NOTE on the two cases below.  We're comparing
#   (a || b) && c   vs.   a || (b && c)
#
# a = true, b = false, c = false is an example where they are different.
# && and || have precedence inside

### precedence of && and || inside [[
[[ True || '' && '' ]] && echo true
# stdout: true

### precedence of && and || in a command context
if test True || test '' && test ''; then
  echo YES
else
  echo "NO precedence"
fi
# stdout: NO precedence

# http://tldp.org/LDP/abs/html/testconstructs.html#DBLBRACKETS

### Octal literals with -eq
decimal=15
octal=017   # = 15 (decimal)
[[ $decimal -eq $octal ]] && echo true
[[ $decimal -eq ZZZ$octal ]] || echo false
# stdout-json: "true\nfalse\n"
# N-I mksh stdout: false
# mksh doesn't implement this syntax for literals.

### Hex literals with -eq
decimal=15
hex=0x0f    # = 15 (decimal)
[[ $decimal -eq $hex ]] && echo true
[[ $decimal -eq ZZZ$hex ]] || echo false
# stdout-json: "true\nfalse\n"
# N-I mksh stdout: false

# TODO: Add tests for this
# https://www.gnu.org/software/bash/manual/bash.html#Bash-Conditional-Expressions
# When used with [[, the ‘<’ and ‘>’ operators sort lexicographically using the current locale. The test command uses ASCII ordering.

### > on strings
# NOTE: < doesn't need space, even though == does?  That's silly.
[[ b>a ]] && echo true
[[ b<a ]] || echo false
# stdout-json: "true\nfalse\n"

### != on strings
# NOTE: b!=a does NOT work
[[ b != a ]] && echo true
[[ a != a ]] || echo false
# stdout-json: "true\nfalse\n"

### -eq on strings 
# This is lame behavior: it does a conversion to 0 first for any string
[[ a -eq a ]] && echo true
[[ a -eq b ]] && echo true
# stdout-json: "true\ntrue\n"
# OK bash/mksh stdout-json: "true\ntrue\n"

### [[ compare with literal -f
var=-f
[[ $var == -f ]] && echo true
[[ '-f' == $var ]] && echo true
# stdout-json: "true\ntrue\n"

### [ compare with literal -f
# Hm this is the same
var=-f
[ $var == -f ] && echo true
[ '-f' == $var ] && echo true
# stdout-json: "true\ntrue\n"

### [[ with op variable
# Parse error -- parsed BEFORE evaluation of vars
op='=='
[[ a $op a ]] && echo true
[[ a $op b ]] || echo false
# status: 2
# OK mksh status: 1

### [ with op variable
# OK -- parsed AFTER evaluation of vars
op='=='
[ a $op a ] && echo true
[ a $op b ] || echo false
# status: 0
# stdout-json: "true\nfalse\n"

### [[ with unquoted empty var
empty=''
[[ $empty == '' ]] && echo true
# stdout: true

### [ with unquoted empty var
empty=''
[ $empty == '' ] && echo true
# status: 2

### [[ at runtime doesn't work
dbracket=[[
$dbracket foo == foo ]]
# status: 127

### [[ with env prefix doesn't work
FOO=bar [[ foo == foo ]]
# status: 127

### [[ over multiple lines is OK
# Hm it seems you can't split anywhere?
[[ foo == foo
&& bar == bar
]] && echo true
# status: 0
# stdout-json: "true\n"

### Argument that looks like a command word operator
[[ -f -f ]] || echo false
[[ -f == ]] || echo false
# stdout-json: "false\nfalse\n"

### Argument that looks like a real operator
[[ -f < ]]
# status: 2
# OK mksh status: 1

### Does user array equal "$@" ?
# Oh it coerces both to a string.  Lame.
# I think it disobeys "${a[@]}", and treats it like an UNQUOTED ${a[@]}.
a=(1 3 5)
b=(1 2 3)
set -- 1 3 5
[[ "$@" = "${a[@]}" ]] && echo true
[[ "$@" = "${b[@]}" ]] || echo false
# stdout-json: "true\nfalse\n"

### Array coerces to string
a=(1 3 5)
[[ '1 3 5' = "${a[@]}" ]] && echo true
[[ '1 3 4' = "${a[@]}" ]] || echo false
# stdout-json: "true\nfalse\n"

### Quotes don't matter in comparison
[[ '3' = 3 ]] && echo true
[[ '3' -eq 3 ]] && echo true
# stdout-json: "true\ntrue\n"

### -eq with arithmetic expression!
[[ 1+2 -eq 3 ]] && echo true
expr='1+2'
[[ $expr -eq 3 ]] && echo true  # must be dynamically parsed
# stdout-json: "true\ntrue\n"

### -eq coercion produces weird results
[[ '' -eq 0 ]] && echo true
# stdout: true

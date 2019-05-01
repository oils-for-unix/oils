#!/usr/bin/env bash
# 
# Tests for the args in:
#
# ${foo:-}
#
# I think the weird single quote behavior is a bug, but everyone agrees.  It's
# a consequence of quote removal.
#
# WEIRD: single quoted default, inside double quotes.  Oh I guess this is
# because double quotes don't treat single quotes as special?
#
# OK here is the issue.  If we have ${} bare, then the default is parsed as
# LexState.OUTER.  If we have "${}", then it's parsed as LexState.DQ.  That
# makes sense I guess.  Vim's syntax highlighting is throwing me off.

#### "${empty:-}"
empty=
argv.py "${empty:-}"
## stdout: ['']

#### ${empty:-}
empty=
argv.py ${empty:-}
## stdout: []

#### array with empty values
declare -a A=('' x "" '')
argv.py "${A[@]}"
## stdout: ['', 'x', '', '']
## N-I dash stdout-json: ""
## N-I dash status: 2
## N-I mksh stdout-json: ""
## N-I mksh status: 1

#### substitution of IFS character, quoted and unquoted
IFS=:
s=:
argv.py $s
argv.py "$s"
## STDOUT:
['']
[':']
## END

#### :-
empty=''
argv.py ${empty:-a} ${Unset:-b}
## stdout: ['a', 'b']

#### -
empty=''
argv.py ${empty-a} ${Unset-b}
# empty one is still elided!
## stdout: ['b']

#### Inner single quotes
argv.py ${Unset:-'b'}
## stdout: ['b']

#### Inner single quotes, outer double quotes
# This is the WEIRD ONE.  Single quotes appear outside.  But all shells agree!
argv.py "${Unset:-'b'}"
## stdout: ["'b'"]

#### Inner double quotes
argv.py ${Unset:-"b"}
## stdout: ['b']

#### Inner double quotes, outer double quotes
argv.py "${Unset-"b"}"
## stdout: ['b']

#### Multiple words: no quotes
argv.py ${Unset:-a b c}
## stdout: ['a', 'b', 'c']

#### Multiple words: no outer quotes, inner single quotes
argv.py ${Unset:-'a b c'}
## stdout: ['a b c']

#### Multiple words: no outer quotes, inner double quotes
argv.py ${Unset:-"a b c"}
## stdout: ['a b c']

#### Multiple words: outer double quotes, no inner quotes
argv.py "${Unset:-a b c}"
## stdout: ['a b c']

#### Multiple words: outer double quotes, inner double quotes
argv.py "${Unset:-"a b c"}"
## stdout: ['a b c']

#### Multiple words: outer double quotes, inner single quotes
argv.py "${Unset:-'a b c'}"
# WEIRD ONE.
## stdout: ["'a b c'"]

#### Mixed inner quotes
argv.py ${Unset:-"a b" c}
## stdout: ['a b', 'c']

#### Mixed inner quotes with outer quotes
argv.py "${Unset:-"a b" c}"
## stdout: ['a b c']

#### part_value tree with multiple words
argv.py ${a:-${a:-"1 2" "3 4"}5 "6 7"}
## stdout: ['1 2', '3 45', '6 7']

#### part_value tree on RHS
v=${a:-${a:-"1 2" "3 4"}5 "6 7"}
argv.py "${v}"
## stdout: ['1 2 3 45 6 7']

#### Var with multiple words: no quotes
var='a b c'
argv.py ${Unset:-$var}
## stdout: ['a', 'b', 'c']

#### Multiple words: no outer quotes, inner single quotes
var='a b c'
argv.py ${Unset:-'$var'}
## stdout: ['$var']

#### Multiple words: no outer quotes, inner double quotes
var='a b c'
argv.py ${Unset:-"$var"}
## stdout: ['a b c']

#### Multiple words: outer double quotes, no inner quotes
var='a b c'
argv.py "${Unset:-$var}"
## stdout: ['a b c']

#### Multiple words: outer double quotes, inner double quotes
var='a b c'
argv.py "${Unset:-"$var"}"
## stdout: ['a b c']

#### Multiple words: outer double quotes, inner single quotes
# WEIRD ONE.
#
# I think I should just disallow any word with single quotes inside double
# quotes.
var='a b c'
argv.py "${Unset:-'$var'}"
## stdout: ["'a b c'"]

#### No outer quotes, Multiple internal quotes
# It's like a single command word.  Parts are joined directly.
var='a b c'
argv.py ${Unset:-A$var " $var"D E F}
## stdout: ['Aa', 'b', 'c', ' a b cD', 'E', 'F']

#### Strip a string with single quotes, unquoted
foo="'a b c d'"
argv.py ${foo%d\'}
## stdout: ["'a", 'b', 'c']

#### Strip a string with single quotes, double quoted
foo="'a b c d'"
argv.py "${foo%d\'}"
## stdout: ["'a b c "]

#### The string to strip is space sensitive
foo='a b c d'
argv.py "${foo%c d}" "${foo%c  d}"
## stdout: ['a b ', 'a b c d']

#### The string to strip can be single quoted, outer is unquoted
foo='a b c d'
argv.py ${foo%'c d'} ${foo%'c  d'}
## stdout: ['a', 'b', 'a', 'b', 'c', 'd']

#### Strip a string with single quotes, double quoted, with unescaped '
# We're in a double quoted context, so we should be able to use a literal
# single quote.  This is very much the case with :-.
foo="'a b c d'"
argv.py "${foo%d'}"
## stdout: ["'a b c "]
## BUG bash/mksh stdout-json: ""
## BUG bash status: 2
## BUG mksh status: 1

#### The string to strip can be single quoted, outer is double quoted
# This is an inconsistency in bash/mksh because '' are treated as literals in
# double quotes.  The correct ways are above.
foo='a b c d'
argv.py "${foo%'c d'}" "${foo%'c  d'}"
## stdout: ['a b c d', 'a b c d']
## BUG bash/mksh stdout: ['a b ', 'a b c d']

#### $'' allowed within VarSub arguments
# Odd behavior of bash/mksh: $'' is recognized but NOT ''!
x=abc
echo ${x%$'b'*}
echo "${x%$'b'*}"  # git-prompt.sh relies on this
## STDOUT:
a
a
## END
## N-I dash STDOUT:
abc
abc
## END

#### # operator with single quoted arg (dash/ash and bash/mksh disagree, reported by Crestwave)
var=a
echo -${var#'a'}-
echo -"${var#'a'}"-
var="'a'"
echo -${var#'a'}-
echo -"${var#'a'}"-
## STDOUT:
--
--
-'a'-
-'a'-
## END
## OK dash/ash STDOUT:
--
-a-
-'a'-
--
## END

#### / operator with single quoted arg (causes syntax error in regex in OSH, reported by Crestwave)
var="++--''++--''"
echo no plus or minus "${var//[+-]}"
echo no plus or minus "${var//['+-']}"
## STDOUT:
no plus or minus ''''
no plus or minus ''''
## END
## status: 0
## OK osh STDOUT:
no plus or minus ''''
## END
## OK osh status: 1
## BUG ash STDOUT:
no plus or minus ''''
no plus or minus ++--++--
## END
## BUG ash status: 0
## N-I dash stdout-json: ""
## N-I dash status: 2

#### single quotes work inside character classes
x='a[[[---]]]b'
echo "${x//['[]']}"
## STDOUT:
a---b
## END
## BUG ash STDOUT:
a[[[---]]]b
## END
## N-I dash stdout-json: ""
## N-I dash status: 2

#### comparison: :- operator with single quoted arg
echo ${unset:-'a'}
echo "${unset:-'a'}"
## STDOUT:
a
'a'
## END

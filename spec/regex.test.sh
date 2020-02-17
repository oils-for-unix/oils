#!/usr/bin/env bash
#
# Only bash and zsh seem to implement [[ foo =~ '' ]]
#
# ^(a b)$ is a regex that should match 'a b' in a group.
#
# Not sure what bash is doing here... I think I have to just be empirical.
# Might need "compat" switch for parsing the regex.  It should be an opaque
# string like zsh, not sure why it isn't.
#
# I think this is just papering over bugs...
# https://www.gnu.org/software/bash/manual/bash.html#Conditional-Constructs
#
# Storing the regular expression in a shell variable is often a useful way to
# avoid problems with quoting characters that are special to the shell. It is
# sometimes difficult to specify a regular expression literally without using
# quotes, or to keep track of the quoting used by regular expressions while
# paying attention to the shell’s quote removal. Using a shell variable to
# store the pattern decreases these problems. For example, the following is
# equivalent to the above:
#
# pattern='[[:space:]]*(a)?b'
# [[ $line =~ $pattern ]]
# 
# If you want to match a character that’s special to the regular expression
# grammar, it has to be quoted to remove its special meaning. This means that in
# the pattern ‘xxx.txt’, the ‘.’ matches any character in the string (its usual
# regular expression meaning), but in the pattern ‘"xxx.txt"’ it can only match a
# literal ‘.’. Shell programmers should take special care with backslashes, since
# backslashes are used both by the shell and regular expressions to remove the
# special meaning from the following character. The following two sets of
# commands are not equivalent: 
#
# From bash code: ( | ) are treated special.  Normally they must be quoted, but
# they can be UNQUOTED in BASH_REGEX state.  In fact they can't be quoted!

#### BASH_REMATCH
[[ foo123 =~ ([a-z]+)([0-9]+) ]]
argv.py "${BASH_REMATCH[@]}"
## STDOUT:
['foo123', 'foo', '123']
## END
## N-I zsh STDOUT:
['']
## END

#### Match is unanchored at both ends
[[ 'bar' =~ a ]] && echo true
## stdout: true

#### Failed match
[[ 'bar' =~ X ]] && echo true
## status: 1
## stdout-json: ""

#### Regex quoted with \ -- preferred in bash
[[ 'a b' =~ ^(a\ b)$ ]] && echo true
## stdout: true

#### Regex quoted with single quotes
# bash doesn't like the quotes
[[ 'a b' =~ '^(a b)$' ]] && echo true
## stdout-json: ""
## status: 1
## OK zsh stdout: true
## OK zsh status: 0

#### Regex quoted with double quotes
# bash doesn't like the quotes
[[ 'a b' =~ "^(a b)$" ]] && echo true
## stdout-json: ""
## status: 1
## OK zsh stdout: true
## OK zsh status: 0

#### Fix single quotes by storing in variable
pat='^(a b)$'
[[ 'a b' =~ $pat ]] && echo true
## stdout: true

#### Fix single quotes by storing in variable
pat="^(a b)$"
[[ 'a b' =~ $pat ]] && echo true
## stdout: true

#### Double quoting pat variable -- again bash doesn't like it.
pat="^(a b)$"
[[ 'a b' =~ "$pat" ]] && echo true
## stdout-json: ""
## status: 1
## OK zsh stdout: true
## OK zsh status: 0

#### Mixing quoted and unquoted parts
[[ 'a b' =~ 'a 'b ]] && echo true
[[ "a b" =~ "a "'b' ]] && echo true
## STDOUT:
true
true
## END

#### Regex with == and not =~ is parse error, different lexer mode required
# They both give a syntax error.  This is lame.
[[ '^(a b)$' == ^(a\ b)$ ]] && echo true
## status: 2
## OK zsh status: 1

#### Omitting ( )
[[ '^a b$' == ^a\ b$ ]] && echo true
## stdout: true

#### Malformed regex
# Are they trying to PARSE the regex?  Do they feed the buffer directly to
# regcomp()?
[[ 'a b' =~ ^)a\ b($ ]] && echo true
## status: 2
## OK zsh status: 1

#### Regex with char class containing space
# For some reason it doesn't work without parens?
[[ 'ba ba ' =~ ([a b]+) ]] && echo true
## stdout: true

#### Operators and space lose meaning inside ()
[[ '< >' =~ (< >) ]] && echo true
## stdout: true
## N-I zsh stdout-json: ""
## N-I zsh status: 1

#### Regex with |
[[ 'bar' =~ foo|bar ]] && echo true
## stdout: true
## N-I zsh stdout-json: ""
## N-I zsh status: 1

#### Regex to match literal brackets []

# bash-completion relies on this, so we're making it match bash.
# zsh understandably differs.
[[ '[]' =~ \[\] ]] && echo true

# Another way to write this.
pat='\[\]'
[[ '[]' =~ $pat ]] && echo true
## STDOUT:
true
true
## END
## OK zsh STDOUT:
true
## END

#### Regex to match literals . ^ $ etc.
[[ 'x' =~ \. ]] || echo false
[[ '.' =~ \. ]] && echo true

[[ 'xx' =~ \^\$ ]] || echo false
[[ '^$' =~ \^\$ ]] && echo true

[[ 'xxx' =~ \+\*\? ]] || echo false
[[ '*+?' =~ \*\+\? ]] && echo true

[[ 'xx' =~ \{\} ]] || echo false
[[ '{}' =~ \{\} ]] && echo true
## STDOUT:
false
true
false
true
false
true
false
true
## END
## BUG zsh STDOUT:
true
false
false
false
## END
## BUG zsh status: 1

#### Unquoted { is a regex parse error
[[ { =~ { ]] && echo true
echo status=$?
## stdout-json: ""
## status: 2
## BUG bash stdout-json: "status=2\n"
## BUG bash status: 0
## BUG zsh stdout-json: "status=1\n"
## BUG zsh status: 0

#### Fatal error inside [[ =~ ]]

# zsh and osh are stricter than bash.  bash treats [[ like a command.

[[ a =~ $(( 1 / 0 )) ]]
echo status=$?
## stdout-json: ""
## status: 1
## BUG bash stdout: status=1
## BUG bash status: 0

#### Quoted { and +
[[ { =~ "{" ]] && echo 'yes {'
[[ + =~ "+" ]] && echo 'yes +'
[[ * =~ "*" ]] && echo 'yes *'
[[ ? =~ "?" ]] && echo 'yes ?'
[[ ^ =~ "^" ]] && echo 'yes ^'
[[ $ =~ "$" ]] && echo 'yes $'
[[ '(' =~ '(' ]] && echo 'yes ('
[[ ')' =~ ')' ]] && echo 'yes )'
[[ '|' =~ '|' ]] && echo 'yes |'
[[ '\' =~ '\' ]] && echo 'yes \'
echo ---

[[ . =~ "." ]] && echo 'yes .'
[[ z =~ "." ]] || echo 'no .'
echo ---

# This rule is weird but all shells agree.  I would expect that the - gets
# escaped?  It's an operator?  but it behaves like a-z.
[[ a =~ ["a-z"] ]]; echo "a $?"
[[ - =~ ["a-z"] ]]; echo "- $?"
[[ b =~ ['a-z'] ]]; echo "b $?"
[[ z =~ ['a-z'] ]]; echo "z $?"

echo status=$?
## STDOUT:
yes {
yes +
yes *
yes ?
yes ^
yes $
yes (
yes )
yes |
yes \
---
yes .
no .
---
a 0
- 1
b 0
z 0
status=0
## END
## N-I zsh STDOUT:
yes ^
yes $
yes )
yes |
---
yes .
---
a 0
- 1
b 0
z 0
status=0
## END

#### Escaped {
# from bash-completion
[[ '$PA' =~ ^(\$\{?)([A-Za-z0-9_]*)$ ]] && argv.py "${BASH_REMATCH[@]}"
## STDOUT:
['$PA', '$', 'PA']
## END
## BUG zsh stdout-json: ""
## BUG zsh status: 1

#### Escaped { stored in variable first
# from bash-completion
pat='^(\$\{?)([A-Za-z0-9_]*)$'
[[ '$PA' =~ $pat ]] && argv.py "${BASH_REMATCH[@]}"
## STDOUT:
['$PA', '$', 'PA']
## END
## BUG zsh STDOUT:
['']
## END

#### regex with ?
[[ 'c' =~ c? ]] && echo true
[[ '' =~ c? ]] && echo true
## STDOUT:
true
true
## END

#### regex with unprintable characters
# can't have nul byte

# This pattern has literal characters
pat=$'^[\x01\x02]+$'

[[ $'\x01\x02\x01' =~ $pat ]]; echo status=$?
[[ $'a\x01' =~ $pat ]]; echo status=$?

# NOTE: There doesn't appear to be any way to escape these!
pat2='^[\x01\x02]+$'

## STDOUT:
status=0
status=1
## END

#### pattern $f(x)  -- regression
f=fff
[[ fffx =~ $f(x) ]]
echo status=$?
[[ ffx =~ $f(x) ]]
echo status=$?
## STDOUT:
status=0
status=1
## END

#### pattern a=(1) 
[[ a=x =~ a=(x) ]]
echo status=$?
[[ =x =~ a=(x) ]]
echo status=$?
## STDOUT:
status=0
status=1
## END
## BUG zsh status: 1
## BUG zsh STDOUT:
status=0
## END

#### pattern @f(x)
shopt -s parse_at
[[ @fx =~ @f(x) ]]
echo status=$?
[[ fx =~ @f(x) ]]
echo status=$?
## STDOUT:
status=0
status=1
## END

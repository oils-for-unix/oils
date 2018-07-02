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
## stdout: true
## status: 0
## OK bash stdout-json: ""
## OK bash status: 1

#### Regex quoted with double quotes
# bash doesn't like the quotes
[[ 'a b' =~ "^(a b)$" ]] && echo true
## stdout: true
## status: 0
## OK bash stdout-json: ""
## OK bash status: 1

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
## stdout: true
## status: 0
## OK bash stdout-json: ""
## OK bash status: 1

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

#### Regex with char class
# For some reason it doesn't work without parens?
[[ 'ba ba ' =~ ([a b]+) ]] && echo true
## stdout: true

#### Operators lose meaning in () in regex state (BASH_REGEX_CAHRS)
[[ '< >' =~ (< >) ]] && echo true
## stdout: true
## N-I zsh stdout-json: ""
## N-I zsh status: 1

#### Regex with |
[[ 'bar' =~ foo|bar ]] && echo true
## stdout: true
## N-I zsh stdout-json: ""
## N-I zsh status: 1

#### Double quoted regex gets regex-escaped
[[ { =~ "{" ]] && echo true
## stdout: true
## N-I zsh status: 1
## N-I zsh stdout-json: ""

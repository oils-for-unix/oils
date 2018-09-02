#!/usr/bin/env bash
#
# Alias is in POSIX.
#
# http://pubs.opengroup.org/onlinepubs/009695399/utilities/xcu_chap02.html#tag_02_03_01
#
# Bash is the only one that doesn't support aliases!

#### Basic alias
shopt -s expand_aliases  # bash requires this
alias hi='echo hello world'
hi || echo 'should not run this'
echo hi  # second word is not
'hi' || echo 'expected failure'
## STDOUT:
hello world
hi
expected failure
## END

#### defining multiple aliases, then unalias
shopt -s expand_aliases  # bash requires this
x=x
y=y
alias echo-x='echo $x' echo-y='echo $y'
echo status=$?
echo-x X
echo-y Y
unalias echo-x echo-y
echo status=$?
echo-x X || echo undefined
echo-y Y || echo undefined
## STDOUT:
status=0
x X
y Y
status=0
undefined
undefined
## END

#### alias not defined
alias e='echo' nonexistentZ
echo status=$?
## STDOUT:
status=1
## END
## OK mksh STDOUT:
nonexistentZ alias not found
status=1
## END

#### unalias not defined
alias e=echo ll='ls -l'
unalias e nonexistentZ ll
echo status=$?
## STDOUT:
status=1
## END

#### listing given aliases
alias e=echo ll='ls -l'
alias e ll
## STDOUT:
alias e='echo'
alias ll='ls -l'
## END
## OK mksh/zsh STDOUT:
e=echo
ll='ls -l'
## END
## OK dash STDOUT:
e='echo'
ll='ls -l'
## END

#### alias without args lists all aliases
alias ex=exit ll='ls -l'
alias | grep -E 'ex=|ll='  # need to grep because mksh/zsh have builtin aliases
echo status=$?
## STDOUT:
alias ex='exit'
alias ll='ls -l'
status=0
## END
## OK dash STDOUT:
ex='exit'
ll='ls -l'
status=0
## END
## OK mksh/zsh STDOUT:
ex=exit
ll='ls -l'
status=0
## END

#### unalias without args is a usage error
unalias
echo status=$?
## stdout: status=2
## BUG mksh/dash stdout: status=0
## BUG zsh stdout: status=1

#### alias with trailing space causes alias expansion on second word
shopt -s expand_aliases  # bash requires this

alias hi='echo hello world '
alias punct='!!!'

hi punct

alias hi='echo hello world'  # No trailing space

hi punct

## STDOUT:
hello world !!!
hello world punct
## END

#### Recursive alias expansion of first word
shopt -s expand_aliases  # bash requires this
alias hi='echo hello world'
alias echo='echo --; echo '
hi   # first hi is expanded to echo hello world; then echo is expanded.  gah.
## STDOUT:
--
hello world
## END

#### Expansion of alias with variable
shopt -s expand_aliases  # bash requires this
x=x
alias echo-x='echo $x'  # nothing is evaluated here
x=y
echo-x hi
## STDOUT:
y hi
## END

#### Alias must be an unquoted word, no expansions allowed
shopt -s expand_aliases  # bash requires this
alias echo_alias_='echo'
cmd=echo_alias_
echo_alias_ X  # this works
$cmd X  # this fails because it's quoted
echo status=$?
## STDOUT:
X
status=127
## END


#### first and second word are the same
shopt -s expand_aliases  # bash requires this
x=x
alias echo-x='echo $x'  # nothing is evaluated here
echo-x echo-x
## STDOUT:
x echo-x
## END
## BUG dash STDOUT:
x echo x
## END

#### first and second word are the same with trailing space
shopt -s expand_aliases  # bash requires this
x=x
alias echo-x='echo $x '  # nothing is evaluated here
echo-x echo-x
## STDOUT:
x echo x
## END


#### Invalid syntax of alias
shopt -s expand_aliases  # bash requires this
alias echo_alias_= 'echo --; echo'  # bad space here
echo_alias_ x
## status: 127

#### Dynamic alias definition
shopt -s expand_aliases  # bash requires this
x=x
name='echo_alias_'
val='=echo'
alias "$name$val"
echo_alias_ X
## stdout: X

#### Alias name with punctuation
# NOTE: / is not OK in bash, but OK in other shells.  Must less restrictive
# than var names.
shopt -s expand_aliases  # bash requires this
alias e_+.~x='echo'
e_+.~x X
## stdout: X

#### Syntax error after expansion
shopt -s expand_aliases  # bash requires this
alias e_=';; oops'
e_ x
## status: 2
## OK mksh/zsh status: 1

#### Loop split across alias and arg works
shopt -s expand_aliases  # bash requires this
alias e_='for i in 1 2 3; do echo $i;'
e_ done
## STDOUT:
1
2
3
## END

#### Loop split across alias in another way is syntax error
# For some reason this doesn't work, but the previous case does.
shopt -s expand_aliases
alias e_='for i in 1 2 3; do echo '
e_ '$i done;'
## status: 2
## OK mksh/zsh status: 1

#### Loop split across both iterative and recursive aliases
shopt -s expand_aliases  # bash requires this
alias FOR1='for '
alias FOR2='FOR1 '
alias eye1='i '
alias eye2='eye1 '
alias IN='in '
alias onetwo='$one "2" '  # NOTE: this does NOT work in any shell except bash.
one=1
FOR2 eye2 IN onetwo 3; do echo $i; done
## STDOUT:
1
2
3
## END
## BUG zsh stdout-json: ""

#### Alias with a quote in the middle is a syntax error
shopt -s expand_aliases
alias e_='echo "'
var=x
e_ '${var}"'
## status: 2
## OK mksh/zsh status: 1

#### Alias with a newline
# The second echo command is run in dash/mksh!
shopt -s expand_aliases
alias e_='echo 1
'
var='echo foo'
e_ ${var}
## stdout-json: "1\nfoo\n"
## OK zsh stdout-json: "1\n"
## OK zsh status: 127

#### Two aliases in pipeline
shopt -s expand_aliases
alias SEQ='seq '
alias THREE='3 '
alias WC='wc '
SEQ THREE | WC -l
## stdout: 3

#### Alias for { block
shopt -s expand_aliases
alias LBRACE='{ '
LBRACE echo one; echo two; }
## STDOUT:
one
two
## END

#### Alias not respected inside $()
# This could be parsed correctly, but it is only defined in a child process.
shopt -s expand_aliases
echo $(alias sayhi='echo hello')
sayhi
## status: 127

#### Alias doesn't work on a single line!
alias sayhi='echo hello'; sayhi same line
sayhi other line
## STDOUT:
hello other line
## END
## BUG bash stdout-json: ""
## BUG bash status: 127

#### Alias is respected inside eval
shopt -s expand_aliases
eval "alias sayhi='echo hello'
sayhi inside"
sayhi outside
## STDOUT:
hello inside
hello outside
## END
## BUG zsh STDOUT:
hello outside
## END

#!/usr/bin/env bash
#
# Alias is in POSIX.
#
# http://pubs.opengroup.org/onlinepubs/009695399/utilities/xcu_chap02.html#tag_02_03_01
#
# Bash is the only one that doesn't support aliases!

### basic alias
shopt -s expand_aliases  # bash requires this
alias hi='echo hello world'
hi
echo hi  # second word is not
## STDOUT:
hello world
hi
## END

### alias with trailing space causes second alias expansion
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

### iterative alias expansion of first word
shopt -s expand_aliases  # bash requires this
alias hi='echo hello world'
alias echo='echo --; echo '
hi   # first hi is expanded to echo hello world; then echo is expanded.  gah.
## STDOUT:
--
hello world
## END


### expansion of alias with value
shopt -s expand_aliases  # bash requires this
x=x
alias echo-x='echo $x'  # nothing is evaluated here
x=y
echo-x hi
## STDOUT:
y hi
## END


### first and second word are the same
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

### first and second word are the same with trailing space
shopt -s expand_aliases  # bash requires this
x=x
alias echo-x='echo $x '  # nothing is evaluated here
echo-x echo-x
## STDOUT:
x echo x
## END

### defining multiple aliases, then unalias
shopt -s expand_aliases  # bash requires this
x=x
y=y
alias echo-x='echo $x' echo-y='echo $y'
echo-x X
echo-y Y
unalias echo-x echo-y
echo-x X || echo undefined
echo-y Y || echo undefined
## STDOUT:
x X
y Y
undefined
undefined
## END


### Invalid syntax of alias
shopt -s expand_aliases  # bash requires this
alias e= 'echo --; echo'  # bad space here
e x
## status: 127

### Dynamic alias definition
shopt -s expand_aliases  # bash requires this
x=x
name='e'
val='=echo'
alias "$name$val"
e X
## stdout: X

### Alias detection happens before expansion
shopt -s expand_aliases  # bash requires this
alias e='echo'
cmd=e
e X
$cmd X
e status=$?
## STDOUT:
X
status=127
## END

### Alias name with punctuation
# NOTE: / is not OK in bash, but OK in other shells.  Must less restrictive
# than var names.
shopt -s expand_aliases  # bash requires this
alias e_.~x='echo'
e_.~x X
## stdout: X
## OK mksh status: 127
## mksh R56 2017/08/08 only allows [][A-Za-z0-9_!%,.@:-] in aliases

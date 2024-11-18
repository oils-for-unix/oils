## oils_failures_allowed: 1
## oils_cpp_failures_allowed: 3
## compare_shells: bash

# NB: This is only for NON-interactive tests of bind. 
# See spec/stateful/bind.py for the remaining tests.

#### bind -l should report readline functions

# This test depends on the exact version

# bind -l | sort > _tmp/this-shell-bind-l.txt
# comm -23 $REPO_ROOT/spec/testdata/bind/bind_l_function_list.txt _tmp/this-shell-bind-l.txt

# More relaxed test
bind -l | grep accept-line

## status: 0
## STDOUT:
accept-line
## END


#### bind -p -P to print function names and key bindings

bind -p | grep menu-complete-backward
echo

bind -P | grep menu-complete-backward

## STDOUT:
"\C-p": menu-complete-backward

menu-complete-backward can be found on "\C-p".
## END

#### bind -s -S accepted

# TODO: add non-trivial tests here

bind -s
bind -S

## STDOUT:
## END

#### bind -v -V accepted

bind -v | grep blink-matching-paren
echo

# transform silly quote so we don't mess up syntax highlighting
bind -V | grep blink-matching-paren | sed "s/\`/'/g"

## STDOUT:
set blink-matching-paren off

blink-matching-paren is set to 'off'
## END

#### bind -q

bind -q zz-bad
echo status=$?

# bash prints message to stdout

bind -q vi-subst
echo status=$?

bind -q menu-complete
echo status=$?

## STDOUT:
status=1
vi-subst is not bound to any keys.
status=1
menu-complete can be invoked via "\C-n".
status=0
## END

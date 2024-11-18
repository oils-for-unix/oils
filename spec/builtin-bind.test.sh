## oils_failures_allowed: 0
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

bind -p | grep accept-line
echo

bind -P | grep accept-line

## STDOUT:
## END

#### bind -s -S accepted

# TODO: add non-trivial tests here

bind -s
bind -S

## STDOUT:
## END

#### bind -v -V accepted

# TODO: add non-trivial tests here

bind -v | grep blink-matching-paren
echo

bind -V | grep blink-matching-paren

## STDOUT:
set blink-matching-paren off

blink-matching-paren is set to `off'
## END

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


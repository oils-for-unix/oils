#!/bin/bash
#
# Test the if statement

### If
if true; then
  echo if
fi
# stdout: if

### else
if false; then
  echo if
else
  echo else
fi
# stdout: else

### elif
if (( 0 )); then
  echo if
elif true; then
  echo elif
else
  echo else
fi
# stdout: elif

### Long style
if [[ 0 -eq 1 ]]
then
  echo if
  echo if
elif true
then
  echo elif
else
  echo else
  echo else
fi
# stdout: elif

# Weird case from bash-help mailing list.
#
# "Evaluations of backticks in if statements".  It doesn't relate to if
# statements but to $?, since && and || behave the same way.

### If empty command
if ''; then echo TRUE; else echo FALSE; fi
# stdout: FALSE
# status: 0

### If subshell true
if `true`; then echo TRUE; else echo FALSE; fi
# stdout: TRUE
# status: 0

### If subshell true WITH OUTPUT is different
if `sh -c 'echo X; true'`; then echo TRUE; else echo FALSE; fi
# stdout: FALSE
# status: 0

### If subshell true WITH ARGUMENT
if `true` X; then echo TRUE; else echo FALSE; fi
# stdout: FALSE
# status: 0

### If subshell false
if `false`; then echo TRUE; else echo FALSE; fi
# stdout: FALSE
# status: 0

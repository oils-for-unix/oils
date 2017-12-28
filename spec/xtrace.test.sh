#!/usr/bin/env bash
#
# xtrace test.  Test PS4 and line numbers, etc.

### basic xtrace
echo 1
set -o xtrace
echo 2
## STDOUT:
1
2
## STDERR:
+ echo 2
## END

### xtrace written before command executes
set -x
echo one >&2
echo two >&2
## stdout-json: ""
## STDERR:
+ echo one
one
+ echo two
two
## OK mksh STDERR:
# mksh traces redirects!
+ >&2 
+ echo one
one
+ >&2 
+ echo two
two
## END

### PS4 is scoped
set -x
echo one
f() { 
  local PS4='- '
  echo func;
}
f
echo two
## STDERR:
+ echo one
+ f
+ local 'PS4=- '
- echo func
+ echo two
## OK dash STDERR:
# dash loses information about spaces!  There is a trailing space, but you
# can't see it.
+ echo one
+ f
+ local PS4=- 
- echo func
+ echo two
## OK mksh STDERR:
# local gets turned into typeset
+ echo one
+ f
+ typeset 'PS4=- '
- echo func
+ echo two
## END

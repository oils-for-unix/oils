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
## END
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
## END

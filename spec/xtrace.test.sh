#!/usr/bin/env bash
#
# xtrace test.  Test PS4 and line numbers, etc.

#### set -o verbose prints unevaluated code
set -o verbose
x=foo
y=bar
echo $x
echo $(echo $y)
## STDOUT:
foo
bar
## STDERR:
x=foo
y=bar
echo $x
echo $(echo $y)
## OK bash STDERR:
x=foo
y=bar
echo $x
echo $(echo $y)
## END

#### xtrace with whitespace and quotes
set -o xtrace
echo '1 2' \' \"
## STDOUT:
1 2 ' "
## STDERR:
+ echo '1 2' \' '"'
## BUG dash STDERR:
+ echo 1 2 ' "
## END

#### CASE: xtrace with newlines
# bash and dash trace this badly.  They print literal newlines, which I don't
# want.
set -x
echo $'[\n]'
## STDOUT:
[
]
## stderr-json: "+ echo $'[\\n]'\n"
## OK bash stderr-json: "+ echo '[\n]'\n"
## N-I dash stdout-json: "$[\n]\n"
## N-I dash stderr-json: "+ echo $[\\n]\n"

#### xtrace written before command executes
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

#### PS4 is scoped
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
## BUG osh STDERR:
# local gets turned into typeset
+ echo one
+ f
- echo func
+ echo two
## END

#### xtrace with variables in PS4
PS4='+$x:'
set -o xtrace
x=1
echo one
x=2
echo two
## STDOUT:
one
two
## STDERR:
+:x=1
+1:echo one
+1:x=2
+2:echo two
## OK mksh STDERR:
# mksh has trailing spaces
+:x=1 
+1:echo one
+1:x=2 
+2:echo two
## OK dash STDERR:
# dash evaluates it earlier
+1:x=1
+1:echo one
+2:x=2
+2:echo two
## OK osh STDERR:
# dash evaluates it earlier
+1:echo one
+2:echo two
## END

#### PS4 with unterminated ${
# osh shows inline error; maybe fail like dash/mksh?
x=1
PS4='+${x'
set -o xtrace
echo one
echo status=$?
## STDOUT:
one
status=0
## END
# mksh and dash both fail.  bash prints errors to stderr.
## OK dash stdout-json: ""
## OK dash status: 2
## OK mksh stdout-json: ""
## OK mksh status: 1

#### PS4 with unterminated $(
# osh shows inline error; maybe fail like dash/mksh?
x=1
PS4='+$(x'
set -o xtrace
echo one
echo status=$?
## STDOUT:
one
status=0
## END
# mksh and dash both fail.  bash prints errors to stderr.
## OK dash stdout-json: ""
## OK dash status: 2
## OK mksh stdout-json: ""
## OK mksh status: 1

#### PS4 with runtime error
# osh shows inline error; maybe fail like dash/mksh?
x=1
PS4='+oops $(( 1 / 0 )) \$'
set -o xtrace
echo one
echo status=$?
## STDOUT:
one
status=0
## END
# mksh and dash both fail.  bash prints errors to stderr.
## OK dash stdout-json: ""
## OK dash status: 2
## OK mksh stdout-json: ""
## OK mksh status: 1


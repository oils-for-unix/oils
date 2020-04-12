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

#### xtrace with unprintable chars
case $SH in (dash) exit ;; esac

s=$'a\x03b\004c\x00d'
set -o xtrace
echo "$s"
## stdout-repr: 'a\x03b\x04c\x00d\n'
## STDERR:
+ echo $'a\x03b\x04c\x00d'
## END
## OK bash stdout-repr: 'a\x03b\x04c\n'
## OK bash stderr-repr: "+ echo $'a\\003b\\004c'\n"

# nonsensical output?
## BUG mksh stdout-repr: 'a;\x04c\r\n'
## BUG mksh stderr-repr: "+ echo $'a;\\004c\\r'\n"
## N-I dash stdout-json: ""
## N-I dash stderr-json: ""

#### xtrace with unicode chars
case $SH in (dash) exit ;; esac

mu1='[μ]'
mu2=$'[\u03bc]'

set -o xtrace
echo "$mu1" "$mu2"

## STDOUT:
[μ] [μ]
## END
## STDERR:
+ echo '[μ]' '[μ]'
## END
## N-I dash stdout-json: ""
## N-I dash stderr-json: ""

#### xtrace with tabs
case $SH in (dash) exit ;; esac

set -o xtrace
echo $'[\t]'
## stdout-json: "[\t]\n"
## STDERR:
+ echo $'[\t]'
## END
# this is a bug because it's hard to see
## BUG bash stderr-json: "+ echo '[\t]'\n"
## N-I dash stdout-json: ""
## N-I dash stderr-json: ""

#### xtrace with whitespace, quotes, and backslash
set -o xtrace
echo '1 2' \' \" \\
## STDOUT:
1 2 ' " \
## END

# Oil is different bceause backslashes require $'\\' and not '\', but that's OK
## STDERR:
+ echo '1 2' $'\'' '"' $'\\'
## END

## OK bash/mksh STDERR:
+ echo '1 2' \' '"' '\'
## END

## BUG dash STDERR:
+ echo 1 2 ' " \
## END

#### xtrace with newlines
# bash and dash trace this badly.  They print literal newlines, which I don't
# want.
set -x
echo $'[\n]'
## STDOUT:
[
]
## STDERR: 
+ echo $'[\n]'
## END
# bash has ugly output that spans lines
## OK bash STDERR:
+ echo '[
]'
## END
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


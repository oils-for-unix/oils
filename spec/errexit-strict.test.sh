#!/bin/bash
#
# Cases relevant to set -o strict-errexit in OSH.
#
# Summary:
# - errexit is reset to false in ash/bash -- completely ignored!
# - local assignment is different than global!  The exit code and errexit
# behavior are different because the concept of the "last command" is
# different.
# - ash has copied bash behavior!

#### command sub: errexit ignored
# This is the bash-specific bug here:
# https://blogs.janestreet.com/when-bash-scripts-bite/
# In bash 4.4, inherit_errexit should fix this.
set -o errexit
echo $(echo one; false; echo two)  # bash/ash keep going
echo status=$?
## STDOUT:
one two
status=0
## END
# dash and mksh: inner shell aborts, but outer one keeps going!
## OK dash/mksh STDOUT:
one
status=0
## END

#### command sub: errexit not ignored with strict-errexit
set -o errexit
set -o strict-errexit || true
echo zero
echo $(echo one; false; echo two)  # bash/ash keep going
echo status=$?
## STDOUT:
zero
## END
## status: 1
## N-I dash status: 2
## N-I dash stdout-json: ""
## N-I mksh stdout-json: ""
## N-I ash/bash status: 0
## N-I ash/bash STDOUT:
zero
one two
status=0
## END

#### command sub: last command fails but keeps going and exit code is 0
set -o errexit
echo $(echo one; false)  # we lost the exit code
echo status=$?
## STDOUT:
one
status=0
## END

#### global assignment with command sub: middle command fails
set -o errexit
s=$(echo one; false; echo two;)
echo "$s"
## status: 0
## STDOUT:
one
two
## END
# dash and mksh: whole thing aborts!
## OK dash/mksh stdout-json: ""
## OK dash/mksh status: 1

#### global assignment with command sub: last command fails and it aborts
set -o errexit
s=$(echo one; false)
echo status=$?
## stdout-json: ""
## status: 1

#### local: middle command fails and keeps going
set -o errexit
f() {
  echo good
  local x=$(echo one; false; echo two)
  echo status=$?
  echo $x
}
f
## STDOUT:
good
status=0
one two
## END
# for dash and mksh, the INNER shell aborts, but the outer one keeps going!
## OK dash/mksh STDOUT:
good
status=0
one
## END

#### local: last command fails and also keeps going
set -o errexit
f() {
  echo good
  local x=$(echo one; false)
  echo status=$?
  echo $x
}
f
## STDOUT:
good
status=0
one
## END

#### local and strict-errexit
# I've run into this problem a lot.
set -o errexit
set -o strict-errexit || true  # ignore error
f() {
  echo good
  local x=$(echo one; false; echo two)
  echo status=$?
  echo $x
}
f
## status: 1
## STDOUT:
good
## END
## N-I bash/ash status: 0
## N-I bash/ash STDOUT:
good
status=0
one two
## END
## N-I dash status: 2
## N-I dash stdout-json: ""
## N-I mksh status: 1
## N-I mksh stdout-json: ""

#### global assignment when last status is failure
# this is a bug I introduced
set -o errexit
[ -n "${BUILDDIR+x}" ] && _BUILDDIR=$BUILDDIR
BUILDDIR=${_BUILDDIR-$BUILDDIR}
echo status=$?
## STDOUT:
status=0
## END

#### global assignment when last status is failure
# this is a bug I introduced
set -o errexit
x=$(false) || true   # from abuild
[ -n "$APORTSDIR" ] && true
BUILDDIR=${_BUILDDIR-$BUILDDIR}
echo status=$?
## STDOUT:
status=0
## END

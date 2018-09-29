#!/usr/bin/env bash
#
# printf
# bash-completion uses this odd printf -v construction.  It seems to mostly use
# %s and %q though.
#
# %s should just be
# declare $var='val'
#
# NOTE: 
# /usr/bin/printf %q "'" seems wrong.
# $ /usr/bin/printf  %q "'"
# ''\'''
#
# I suppose it is technically correct, but it looks very ugly.

#### printf -v %s
var=foo
printf -v $var %s 'hello there'
argv "$foo" 
## STDOUT:
['hello there']
## END

#### printf -v %q
var=foo
printf -v $var %q '"quoted" with spaces and \'
argv "$foo" 
## STDOUT:
['\\"quoted\\"\\ with\\ spaces\\ and\\ \\\\']
## END

#### declare instead of %s
var=foo
declare $var='hello there'
argv "$foo" 
## STDOUT:
['hello there']
## END

#### declare instead of %q
var=foo
val='"quoted" with spaces and \'
# I think this is bash 4.4 only.
declare $var="${val@Q}"
argv "$foo" 
## STDOUT:
['hello there']
## END

#### printf -v dynamic scope
# OK so printf is like assigning to a var.
# printf -v foo %q "$bar" is like
# foo=${bar@Q}
dollar='dollar'
f() {
  local mylocal=foo
  printf -v dollar %q '$'  # assign foo to a quoted dollar
  printf -v mylocal %q 'mylocal'
  echo dollar=$dollar
  echo mylocal=$mylocal
}
echo dollar=$dollar
echo --
f
echo --
echo dollar=$dollar
echo mylocal=$mylocal
## STDOUT:
dollar=dollar
--
dollar=\$
mylocal=mylocal
--
dollar=\$
mylocal=
## END


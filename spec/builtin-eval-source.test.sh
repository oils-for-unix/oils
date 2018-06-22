#!/usr/bin/env bash

### Eval
eval "a=3"
echo $a
# stdout: 3

### Source
lib=$TMP/spec-test-lib.sh
echo 'LIBVAR=libvar' > $lib
. $lib  # dash doesn't have source
echo $LIBVAR
# stdout: libvar

### Source nonexistent
source /nonexistent/path
echo status=$?
# stdout: status=1
# OK dash/zsh stdout: status=127

### Source with no arguments
source
echo status=$?
# stdout: status=1
# OK bash stdout: status=2
# OK dash stdout: status=127

### Source with arguments
. spec/testdata/show-argv.sh foo bar  # dash doesn't have source
## STDOUT:
show-argv: foo bar
## END
## N-I dash STDOUT:
show-argv:
## END

### Source from a function, mutating argv and defining a local var
f() {
  . spec/testdata/source-argv.sh              # no argv
  . spec/testdata/source-argv.sh args to src  # new argv
  echo $@
  echo foo=$foo  # defined in source-argv.sh
}
f args to func
echo foo=$foo  # not defined
## STDOUT:
source-argv: args to func
source-argv: args to src
to func
foo=foo_val
foo=
## END
## N-I dash STDOUT:
source-argv: args to func
source-argv: to func
func
foo=foo_val
foo=
## END

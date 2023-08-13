## oils_failures_allowed: 1
## compare_shells: bash

#### $SHELL set to login shell

sh=$(which $SH)

unset SHELL

prog='
if test -n "$SHELL"; then
  # the exact value is different on CI, so do not assert
  echo SHELL is set
  echo SHELL=$SHELL >&2
fi
'

$SH -c "$prog"

# make it a login shell
$SH -l -c "$prog"

## STDOUT:
SHELL is set
SHELL is set
## END
## N-I dash/mksh/zsh STDOUT:
SHELL=
SHELL=
## END

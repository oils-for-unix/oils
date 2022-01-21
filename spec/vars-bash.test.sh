#### $SHELL set to login shell

sh=$(which $SH)

unset SHELL

$SH -c 'echo SHELL=$SHELL'

# make it a login shell
$SH -l -c 'echo SHELL=$SHELL'

## STDOUT:
SHELL=/bin/bash
SHELL=/bin/bash
## END
## N-I dash/mksh/zsh STDOUT:
SHELL=
SHELL=
## END

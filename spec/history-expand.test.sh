## compare_shells: bash

#### !! expansion

# file in this test case directory
HISTFILE=myhistory

i-shell() {
  $SH --rcfile /dev/null "$@"
}

# -i -c is not interactive
i-shell -i -c '
echo one
echo !!
'

# -i is interactive
echo '
echo two
echo !!
exit
' | i-shell -i

## STDOUT:
one
!!
two
echo two
## END

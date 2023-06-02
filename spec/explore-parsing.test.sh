#
# Tests that explore parsing corner cases.

#### Length of length of ARGS!
fun() { echo ${##}; }
fun 0 1 2 3 4 5 6 7 8 
## stdout: 1

#### Length of length of ARGS!  2 digit
fun() { echo ${##}; }
fun 0 1 2 3 4 5 6 7 8 9
## stdout: 2

#### Is \r considered whitespace?
echo -e 'echo\rTEST' > myscript
$SH myscript

## status: 127
## STDOUT:
## END

#### readonly +

# dash and bash validate this!  But not set +

readonly + >/dev/null
echo status=$?
## STDOUT:
status=0
## END
## OK bash STDOUT:
status=1
## END
## OK dash status: 2
## OK dash stdout-json: ""

#### set +
set + >/dev/null
echo status=$?
## STDOUT:
status=0
## END

#### interactive parsing
case $SH in zsh) exit ;; esac

export PS1='[PS1]'

echo 'if true
then
  echo hi
fi' | $SH -i

if test -z "$OILS_VERSION"; then
  echo '^D'  # fudge
fi

## STDOUT:
hi
^D
## END

## stderr-json: "[PS1]> > > [PS1]"

# hm somehow bash prints it more nicely; code is echo'd to stderr

## OK bash STDERR:
[PS1]if true
> then
>   echo hi
> fi
[PS1]exit
## END

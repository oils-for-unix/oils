#### history -a
rm -f tmp

echo '
history -c

HISTFILE=tmp
echo 1
history -a
cat tmp

echo 2

cat tmp
' | $SH -i

# match osh's behaviour of echoing ^D for EOF
case $SH in bash) echo '^D' ;; esac

## STDOUT:
1
HISTFILE=tmp
echo 1
history -a
2
HISTFILE=tmp
echo 1
history -a
^D
## END

#### history -r
rm -f tmp
echo 'foo' > tmp

echo '
history -c

HISTFILE=tmp
history -r
history
' | $SH -i

# match osh's behaviour of echoing ^D for EOF
case $SH in bash) echo '^D' ;; esac

## STDOUT:
    1  HISTFILE=tmp
    2  history -r
    3  foo
    4  history
^D
## END

#### HISTFILE is defined initially
echo '
if test -n $HISTFILE; then echo exists; fi
' | $SH -i

# match osh's behaviour of echoing ^D for EOF
case $SH in bash) echo '^D' ;; esac

## STDOUT:
exists
^D
## END

#### HISTFILE must be a string

# TODO: we should support bash's behaviour here

echo '
HISTFILE=(a b c)
history -r
echo $?
' | $SH -i

## STDOUT:
0
## END
## OK osh STDOUT:
1
^D
## END

#### history -d to delete history item

# TODO: Respect HISTFILE and fix this test

history -d 1
echo status=$?

# problem: default for integers is -1
history -d -1
echo status=$?
history -d -2
echo status=$?

## STDOUT:
status=0
status=1
status=1
## END

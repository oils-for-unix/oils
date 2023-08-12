## tags: interactive
## compare_shells: bash

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

#### HISTFILE must point to a file

rm -f _tmp/does-not-exist

echo '
HISTFILE=_tmp/does-not-exist
history -r
echo status=$?
' | $SH -i

# match osh's behaviour of echoing ^D for EOF
case $SH in bash) echo '^D' ;; esac

## STDOUT:
status=1
^D
## END

#### HISTFILE set to array

echo '
HISTFILE=(a b c)
history -a
echo status=$?
' | $SH -i

case $SH in bash) echo '^D' ;; esac

# note that bash actually writes the file 'a', since that's ${HISTFILE[0]} 

## STDOUT:
status=1
^D
## END

## OK bash STDOUT:
status=0
^D
## END

#### HISTFILE unset

echo '
unset HISTFILE
history -a
echo status=$?
' | $SH -i

case $SH in bash) echo '^D' ;; esac

## STDOUT:
status=1
^D
## END


#### history -d to delete history item

rm -f myhist
export HISTFILE=myhist

$SH --norc -i <<'EOF'

echo 42
echo 43
echo 44

history -a

history -d 1
echo status=$?

# Invalid integers
history -d -1
echo status=$?
history -d -2
echo status=$?
history -d 99
echo status=$?

case $SH in bash) echo '^D' ;; esac

EOF

## STDOUT:
42
43
44
status=0
status=2
status=2
status=2
^D
## END

## OK bash STDOUT:
42
43
44
status=0
status=1
status=1
status=1
^D
## END

#### history usage

history not-a-number
echo status=$?

history 3 too-many
echo status=$?

## STDOUT:
status=2
status=2
## END

## OK bash STDOUT:
status=1
status=1
## END




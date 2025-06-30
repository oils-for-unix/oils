## tags: interactive
## compare_shells: bash
## oils_failures_allowed: 2

#### fc -l lists history commands
rm -f tmp

echo '
HISTFILE=tmp
seq 3 > tmp
history -c
history -r

fc -l
' | $SH --norc -i

# match osh's behaviour of echoing ^D for EOF
case $SH in bash) echo '^D' ;; esac

## STDOUT:
1	 history -r
2	 1
3	 2
4	 3
^D
## END

#### fc -ln lists history commands without numbers
rm -f tmp

echo '
HISTFILE=tmp
seq 3 > tmp
history -c
history -r

fc -ln
' | $SH --norc -i

# match osh's behaviour of echoing ^D for EOF
case $SH in bash) echo '^D' ;; esac

## STDOUT:
	 history -r
	 1
	 2
	 3
^D
## END

#### fc -lr lists history commands in reverse order
rm -f tmp

echo '
HISTFILE=tmp
seq 3 > tmp
history -c
history -r

fc -lr
' | $SH --norc -i

# match osh's behaviour of echoing ^D for EOF
case $SH in bash) echo '^D' ;; esac

## STDOUT:
4	 3
3	 2
2	 1
1	 history -r
^D
## END

#### fc -lnr lists history commands without numbers in reverse order
rm -f tmp

echo '
HISTFILE=tmp
seq 3 > tmp
history -c
history -r

fc -lnr
' | $SH --norc -i

# match osh's behaviour of echoing ^D for EOF
case $SH in bash) echo '^D' ;; esac

## STDOUT:
	 3
	 2
	 1
	 history -r
^D
## END

#### fc -l lists history commands with default page size
rm -f tmp

echo '
HISTFILE=tmp
seq 16 > tmp
history -c
history -r

fc -l
' | $SH --norc -i

# match osh's behaviour of echoing ^D for EOF
case $SH in bash) echo '^D' ;; esac

## STDOUT:
2	 1
3	 2
4	 3
5	 4
6	 5
7	 6
8	 7
9	 8
10	 9
11	 10
12	 11
13	 12
14	 13
15	 14
16	 15
17	 16
^D
## END

#### fc -l [first] where first is an index
rm -f tmp

echo '
HISTFILE=tmp
seq 3 > tmp
history -c
history -r

fc -l 2
' | $SH --norc -i

# match osh's behaviour of echoing ^D for EOF
case $SH in bash) echo '^D' ;; esac

## STDOUT:
2	 1
3	 2
4	 3
^D
## END

#### fc -l [first] where first is an offset from current command
rm -f tmp

echo '
HISTFILE=tmp
seq 3 > tmp
history -c
history -r

fc -l -3
' | $SH --norc -i

# match osh's behaviour of echoing ^D for EOF
case $SH in bash) echo '^D' ;; esac

## STDOUT:
2	 1
3	 2
4	 3
^D
## END

#### fc -l [first] [last] where first and last are indexes
rm -f tmp

echo '
HISTFILE=tmp
seq 3 > tmp
history -c
history -r

fc -l 2 3
' | $SH --norc -i

# match osh's behaviour of echoing ^D for EOF
case $SH in bash) echo '^D' ;; esac

## STDOUT:
2	 1
3	 2
^D
## END

#### fc -l [first] [last] where first and last are offsets from current command
rm -f tmp

echo '
HISTFILE=tmp
seq 3 > tmp
history -c
history -r

fc -l -3 -2
' | $SH --norc -i

# match osh's behaviour of echoing ^D for EOF
case $SH in bash) echo '^D' ;; esac

## STDOUT:
2	 1
3	 2
^D
## END

#### fc -l [first] [last] where first and last are reversed indexes
rm -f tmp

echo '
HISTFILE=tmp
seq 3 > tmp
history -c
history -r

fc -l 3 2
' | $SH --norc -i

# match osh's behaviour of echoing ^D for EOF
case $SH in bash) echo '^D' ;; esac

## STDOUT:
3	 2
2	 1
^D
## END

#### fc -lr [first] [last] where first and last are reversed indexes does not undo reverse
rm -f tmp

echo '
HISTFILE=tmp
seq 3 > tmp
history -c
history -r

fc -lr 3 2
' | $SH --norc -i

# match osh's behaviour of echoing ^D for EOF
case $SH in bash) echo '^D' ;; esac

## STDOUT:
3	 2
2	 1
^D
## END

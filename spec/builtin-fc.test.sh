## tags: interactive
## compare_shells: bash
## oils_failures_allowed: 2

#### fc -l lists history commands
printf "echo %s\n" {1..3} > tmp

echo '
HISTFILE=tmp
history -c
history -r

fc -l
' | $SH --norc -i

# match osh's behaviour of echoing ^D for EOF
case $SH in bash) echo '^D' ;; esac

## STDOUT:
1	 history -r
2	 echo 1
3	 echo 2
4	 echo 3
^D
## END

#### fc -ln lists history commands without numbers
printf "echo %s\n" {1..3} > tmp

echo '
HISTFILE=tmp
history -c
history -r

fc -ln
' | $SH --norc -i

# match osh's behaviour of echoing ^D for EOF
case $SH in bash) echo '^D' ;; esac

## STDOUT:
	 history -r
	 echo 1
	 echo 2
	 echo 3
^D
## END

#### fc -lr lists history commands in reverse order
printf "echo %s\n" {1..3} > tmp

echo '
HISTFILE=tmp
history -c
history -r

fc -lr
' | $SH --norc -i

# match osh's behaviour of echoing ^D for EOF
case $SH in bash) echo '^D' ;; esac

## STDOUT:
4	 echo 3
3	 echo 2
2	 echo 1
1	 history -r
^D
## END

#### fc -lnr lists history commands without numbers in reverse order
printf "echo %s\n" {1..3} > tmp

echo '
HISTFILE=tmp
history -c
history -r

fc -lnr
' | $SH --norc -i

# match osh's behaviour of echoing ^D for EOF
case $SH in bash) echo '^D' ;; esac

## STDOUT:
	 echo 3
	 echo 2
	 echo 1
	 history -r
^D
## END

#### fc -l lists history commands with default page size
printf "echo %s\n" {1..16} > tmp

echo '
HISTFILE=tmp
history -c
history -r

fc -l
' | $SH --norc -i

# match osh's behaviour of echoing ^D for EOF
case $SH in bash) echo '^D' ;; esac

## STDOUT:
2	 echo 1
3	 echo 2
4	 echo 3
5	 echo 4
6	 echo 5
7	 echo 6
8	 echo 7
9	 echo 8
10	 echo 9
11	 echo 10
12	 echo 11
13	 echo 12
14	 echo 13
15	 echo 14
16	 echo 15
17	 echo 16
^D
## END

#### fc -l [first] where first is an index
printf "echo %s\n" {1..3} > tmp

echo '
HISTFILE=tmp
history -c
history -r

fc -l 2
' | $SH --norc -i

# match osh's behaviour of echoing ^D for EOF
case $SH in bash) echo '^D' ;; esac

## STDOUT:
2	 echo 1
3	 echo 2
4	 echo 3
^D
## END

#### fc -l [first] where first is an offset from current command
printf "echo %s\n" {1..3} > tmp

echo '
HISTFILE=tmp
history -c
history -r

fc -l -3
' | $SH --norc -i

# match osh's behaviour of echoing ^D for EOF
case $SH in bash) echo '^D' ;; esac

## STDOUT:
2	 echo 1
3	 echo 2
4	 echo 3
^D
## END

#### fc -l [first] [last] where first and last are indexes
printf "echo %s\n" {1..3} > tmp

echo '
HISTFILE=tmp
history -c
history -r

fc -l 2 3
' | $SH --norc -i

# match osh's behaviour of echoing ^D for EOF
case $SH in bash) echo '^D' ;; esac

## STDOUT:
2	 echo 1
3	 echo 2
^D
## END

#### fc -l [first] [last] where first and last are offsets from current command
printf "echo %s\n" {1..3} > tmp

echo '
HISTFILE=tmp
history -c
history -r

fc -l -3 -2
' | $SH --norc -i

# match osh's behaviour of echoing ^D for EOF
case $SH in bash) echo '^D' ;; esac

## STDOUT:
2	 echo 1
3	 echo 2
^D
## END

#### fc -l [first] [last] where first and last are reversed indexes
printf "echo %s\n" {1..3} > tmp

echo '
HISTFILE=tmp
history -c
history -r

fc -l 3 2
' | $SH --norc -i

# match osh's behaviour of echoing ^D for EOF
case $SH in bash) echo '^D' ;; esac

## STDOUT:
3	 echo 2
2	 echo 1
^D
## END

#### fc -lr [first] [last] where first and last are reversed indexes does not undo reverse
printf "echo %s\n" {1..3} > tmp

echo '
HISTFILE=tmp
history -c
history -r

fc -lr 3 2
' | $SH --norc -i

# match osh's behaviour of echoing ^D for EOF
case $SH in bash) echo '^D' ;; esac

## STDOUT:
3	 echo 2
2	 echo 1
^D
## END

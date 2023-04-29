
#### command -v
myfunc() { echo x; }
command -v echo
echo $?
command -v myfunc
echo $?
command -v nonexistent  # doesn't print anything
echo $?
command -v for
echo $?
## STDOUT:
echo
0
myfunc
0
1
for
0
## OK dash STDOUT:
echo
0
myfunc
0
127
for
0
## END

#### command -v with multiple names
# ALL FOUR SHELLS behave differently here!
#
# bash chooses to swallow the error!  We agree with zsh if ANY word lookup
# fails, then the whole thing fails.

myfunc() { echo x; }
command -v echo myfunc ZZZ for
echo status=$?

## STDOUT:
echo
myfunc
for
status=1
## BUG bash STDOUT:
echo
myfunc
for
status=0
## BUG dash STDOUT: 
echo
status=0
## OK mksh STDOUT: 
echo
myfunc
status=1
## END

#### command -v doesn't find non-executable file
# PATH resolution is different

PATH="$TMP:$PATH"
touch $TMP/non-executable $TMP/executable
chmod +x $TMP/executable

command -v non-executable | grep -o /non-executable
echo status=$?

command -v executable | grep -o /executable
echo status=$?

## STDOUT:
status=1
/executable
status=0
## END

## BUG bash/dash STDOUT:
/non-executable
status=0
/executable
status=0
## END

#### command skips function lookup
seq() {
  echo "$@"
}
command  # no-op
seq 3
command seq 3
# subshell shouldn't fork another process (but we don't have a good way of
# testing it)
( command seq 3 )
## STDOUT:
3
1
2
3
1
2
3
## END

#### command command seq 3
command command seq 3
## STDOUT:
1
2
3
## END
## N-I zsh stdout-json: ""
## N-I zsh status: 127

#### command command -v seq
seq() {
  echo 3
}
command command -v seq
## stdout: seq
## N-I zsh stdout-json: ""
## N-I zsh status: 127

#### history -a
case $SH in dash|mksh|zsh) exit 0 ;; esac

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
## N-I dash/mksh/zsh STDOUT:
## END

#### history -r
case $SH in dash|mksh|zsh) exit 0 ;; esac

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
## N-I dash/mksh/zsh STDOUT:
## END

#### HISTFILE is defined initially
case $SH in zsh) exit 0 ;; esac

echo '
if test -n $HISTFILE; then echo exists; fi
' | $SH -i

# match osh's behaviour of echoing ^D for EOF
case $SH in bash|mksh|dash) echo '^D' ;; esac

## STDOUT:
exists
^D
## END
## N-I zsh STDOUT:
## END

#### HISTFILE must be a string
case $SH in bash|mksh|dash|zsh) exit 0 ;; esac

echo '
HISTFILE=(a b c)
history -r
echo $?
' | $SH -i

## STDOUT:
1
^D
## END
## N-I bash/mksh/dash/zsh STDOUT:
## END

#### history usage
history
echo status=$?
history +5  # hm bash considers this valid
echo status=$?
history -5  # invalid flag
echo status=$?
history f 
echo status=$?
history too many args
echo status=$?
## status: 0
## STDOUT:
status=0
status=0
status=2
status=2
status=2
## END
## OK bash STDOUT:
status=0
status=0
status=2
status=1
status=1
## END
## BUG zsh/mksh STDOUT:
status=1
status=1
status=1
status=1
status=1
## END
## N-I dash STDOUT:
status=127
status=127
status=127
status=127
status=127
## END

#### history -d to delete history item

# TODO: Respect HISTFILE and fix this test

case $SH in (dash|mksh|zsh) exit ;; esac

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
## N-I dash/mksh/zsh stdout-json: ""

#### $(command type ls)
type() { echo FUNCTION; }
type
s=$(command type echo)
echo $s | grep builtin > /dev/null
echo status=$?
## STDOUT:
FUNCTION
status=0
## END
## N-I zsh STDOUT:
FUNCTION
status=1
## END
## N-I mksh STDOUT:
status=1
## END

#### builtin
cd () { echo "hi"; }
cd
builtin cd / && pwd
unset -f cd
## STDOUT:
hi
/
## END
## N-I dash STDOUT:
hi
## END

#### builtin ls not found
builtin ls
## status: 1
## N-I dash status: 127

#### builtin no args
builtin
## status: 0
## N-I dash status: 127

#### builtin command echo hi
builtin command echo hi
## status: 0
## stdout: hi
## N-I dash status: 127
## N-I dash stdout-json: ""

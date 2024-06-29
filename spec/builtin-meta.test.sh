## oils_failures_allowed: 1
## compare_shells: dash bash mksh zsh

#### command -v
myfunc() { echo x; }
command -v echo
echo $?

command -v myfunc
echo $?

command -v nonexistent  # doesn't print anything
echo nonexistent=$?

command -v ''  # BUG FIX, shouldn't succeed
echo empty=$?

command -v for
echo $?

## STDOUT:
echo
0
myfunc
0
nonexistent=1
empty=1
for
0
## OK dash STDOUT:
echo
0
myfunc
0
nonexistent=127
empty=127
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

PATH="_tmp:$PATH"
touch _tmp/non-executable _tmp/executable
chmod +x _tmp/executable

command -v _tmp/non-executable
echo status=$?

command -v _tmp/executable
echo status=$?

## STDOUT:
status=1
_tmp/executable
status=0
## END

## BUG dash STDOUT:
_tmp/non-executable
status=0
_tmp/executable
status=0
## END

#### command -V
myfunc() { echo x; }

shopt -s expand_aliases
alias ll='ls -l'

backtick=\`
command -V ll | sed "s/$backtick/'/g"
echo status=$?

command -V echo
echo status=$?

command -V myfunc
echo status=$?

command -V nonexistent  # doesn't print anything
echo status=$?

command -V for
echo status=$?

## STDOUT:
ll is an alias for "ls -l"
status=0
echo is a shell builtin
status=0
myfunc is a shell function
status=0
status=1
for is a shell keyword
status=0
## END

## OK zsh STDOUT:
ll is an alias for ls -l
status=0
echo is a shell builtin
status=0
myfunc is a shell function
status=0
nonexistent not found
status=1
for is a reserved word
status=0
## END

## OK bash STDOUT:
ll is aliased to 'ls -l'
status=0
echo is a shell builtin
status=0
myfunc is a function
myfunc () 
{ 
    echo x
}
status=0
status=1
for is a shell keyword
status=0
## END

## OK mksh STDOUT:
ll is an alias for 'ls -l'
status=0
echo is a shell builtin
status=0
myfunc is a function
status=0
nonexistent not found
status=1
for is a reserved word
status=0
## END

## OK dash STDOUT:
ll is an alias for ls -l
status=0
echo is a shell builtin
status=0
myfunc is a shell function
status=0
nonexistent: not found
status=127
for is a shell keyword
status=0
## END

#### command -V nonexistent
command -V nonexistent 2>err.txt
echo status=$?
fgrep -o 'nonexistent: not found' err.txt || true

## STDOUT:
status=1
nonexistent: not found
## END

## OK zsh/mksh STDOUT:
nonexistent not found
status=1
## END

## BUG dash STDOUT:
nonexistent: not found
status=127
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

#### command -p (override existing program)
# Tests whether command -p overrides the path
# tr chosen because we need a simple non-builtin
mkdir -p $TMP/bin
echo "echo wrong" > $TMP/bin/tr
chmod +x $TMP/bin/tr
PATH="$TMP/bin:$PATH"
echo aaa | tr "a" "b"
echo aaa | command -p tr "a" "b"
rm $TMP/bin/tr
## STDOUT:
wrong
bbb
## END

#### command -p (hide tool in custom path)
mkdir -p $TMP/bin
echo "echo hello" > $TMP/bin/hello
chmod +x $TMP/bin/hello
export PATH=$TMP/bin
command -p hello
## status: 127 

#### command -p (find hidden tool in default path)
export PATH=''
command -p ls
## status: 0


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

#### builtin typeset / export / readonly
case $SH in dash) exit ;; esac

builtin typeset s=typeset
echo s=$s

builtin export s=export
echo s=$s

builtin readonly s=readonly
echo s=$s

echo --

builtin builtin typeset s2=typeset
echo s2=$s2

builtin builtin export s2=export
echo s2=$s2

builtin builtin readonly s2=readonly
echo s2=$s2

## STDOUT:
s=typeset
s=export
s=readonly
--
s2=typeset
s2=export
s2=readonly
## END
## N-I dash STDOUT:
## END

#### builtin declare / local
case $SH in dash|mksh) exit ;; esac

builtin declare s=declare
echo s=$s

f() {
  builtin local s=local
  echo s=$s
}

f

## STDOUT:
s=declare
s=local
## END
## N-I dash/mksh STDOUT:
## END

#### builtin declare etc. with array is not parsed

$SH -c 'builtin declare a=(x y)'
test $? -ne 0 && echo 'fail'

$SH -c 'builtin declare -a a=(x y)'
test $? -ne 0 && echo 'fail'

## STDOUT:
fail
fail
## END

#### command export / readonly
case $SH in zsh) exit ;; esac

# dash doesn't have declare typeset

command export c=export
echo c=$c

command readonly c=readonly
echo c=$c

echo --

command command export cc=export
echo cc=$cc

command command readonly cc=readonly
echo cc=$cc

## STDOUT:
c=export
c=readonly
--
cc=export
cc=readonly
## END
## N-I zsh STDOUT:
## END

#### command local

f() {
  command local s=local
  echo s=$s
}

f

## STDOUT:
s=local
## END
## BUG dash/mksh/zsh STDOUT:
s=
## END


#### static builtin command ASSIGN, command builtin ASSIGN
case $SH in dash|zsh) exit ;; esac

# dash doesn't have declare typeset

builtin command export bc=export
echo bc=$bc

builtin command readonly bc=readonly
echo bc=$bc

echo --

command builtin export cb=export
echo cb=$cb

command builtin readonly cb=readonly
echo cb=$cb

## STDOUT:
bc=export
bc=readonly
--
cb=export
cb=readonly
## END
## N-I dash/zsh STDOUT:
## END

#### dynamic builtin command ASSIGN, command builtin ASSIGN
case $SH in dash|zsh) exit ;; esac

b=builtin
c=command
e=export
r=readonly

$b $c export bc=export
echo bc=$bc

$b $c readonly bc=readonly
echo bc=$bc

echo --

$c $b export cb=export
echo cb=$cb

$c $b readonly cb=readonly
echo cb=$cb

echo --

$b $c $e bce=export
echo bce=$bce

$b $c $r bcr=readonly
echo bcr=$bcr

echo --

$c $b $e cbe=export
echo cbe=$cbe

$c $b $r cbr=readonly
echo cbr=$cbr

## STDOUT:
bc=export
bc=readonly
--
cb=export
cb=readonly
--
bce=export
bcr=readonly
--
cbe=export
cbr=readonly
## END
## N-I dash/zsh STDOUT:
## END


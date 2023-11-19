## oils_failures_allowed: 1

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

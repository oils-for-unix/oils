## oils_failures_allowed: 3
## compare_shells: dash bash mksh zsh


#### Print shell strings with weird chars: set and printf %q and ${x@Q}

# bash declare -p will print binary data, which makes this invalid UTF-8!
foo=$(/bin/echo -e 'a\nb\xffc'\'d)

# let's test the easier \x01, which doesn't give bash problems
foo=$(/bin/echo -e 'a\nb\x01c'\'d)

# dash:
#   only supports 'set'; prints it on multiple lines with binary data
#   switches to "'" for single quotes, not \'
# zsh:
#   print binary data all the time, except for printf %q
#   does print $'' strings
# mksh:
#   prints binary data for @Q
#   prints $'' strings

# All are very inconsistent.

case $SH in dash|mksh|zsh) return ;; esac


set | grep -A1 foo

# Will print multi-line and binary data literally!
#declare -p foo

printf 'pf  %q\n' "$foo"

echo '@Q ' ${foo@Q}

## STDOUT:
foo=$'a\nb\x01c\'d'
pf  $'a\nb\x01c\'d'
@Q  $'a\nb\x01c\'d'
## END

## OK bash STDOUT:
foo=$'a\nb\001c\'d'
pf  $'a\nb\001c\'d'
@Q  $'a\nb\001c\'d'
## END

## OK dash/mksh/zsh STDOUT:
## END

#### Print shell strings with normal chars: set and printf %q and ${x@Q}

# There are variations on whether quotes are printed

case $SH in dash|zsh) return ;; esac

foo=spam

set | grep -A1 foo

# Will print multi-line and binary data literally!
typeset -p foo

printf 'pf  %q\n' "$foo"

echo '@Q ' ${foo@Q}

## STDOUT:
foo=spam
declare -- foo=spam
pf  spam
@Q  spam
## END


## OK bash STDOUT:
foo=spam
declare -- foo="spam"
pf  spam
@Q  'spam'
## END

## OK mksh STDOUT:
foo=spam
typeset foo=spam
pf  spam
@Q  spam
## END

## N-I dash/zsh STDOUT:
## END



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
ll is an alias for 'ls -l'
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

#!/usr/bin/env bash

#### >&
echo hi 1>&2
## stderr: hi

#### <&
# Is there a simpler test case for this?
echo foo > $TMP/lessamp.txt
exec 6< $TMP/lessamp.txt
read line <&6
echo "[$line]"
## stdout: [foo]

#### Leading redirect
echo hello >$TMP/hello.txt  # temporary fix
<$TMP/hello.txt cat
## stdout: hello

#### Nonexistent file
cat <$TMP/nonexistent.txt
echo status=$?
## stdout: status=1
## OK dash stdout: status=2

#### Redirect in command sub
FOO=$(echo foo 1>&2)
echo $FOO
## stdout:
## stderr: foo

#### Redirect in assignment
# dash captures stderr to a file here, which seems correct.  Bash doesn't and
# just lets it go to actual stderr.
# For now we agree with dash/mksh, since it involves fewer special cases in the
# code.

FOO=$(echo foo 1>&2) 2>$TMP/no-command.txt
echo FILE=
cat $TMP/no-command.txt
echo "FOO=$FOO"
## STDOUT:
FILE=
foo
FOO=
## END
## BUG bash STDOUT:
FILE=
FOO=
## END

#### Redirect in function body.
fun() { echo hi; } 1>&2
fun
## stdout-json: ""
## stderr-json: "hi\n"

#### Bad redirects in function body
empty=''
fun() { echo hi; } > $empty
fun
echo status=$?
## stdout: status=1
## OK dash stdout: status=2

#### Redirect in function body is evaluated multiple times
i=0
fun() { echo "file $i"; } 1> "$TMP/file$((i++))"
fun
fun
echo i=$i
echo __
cat $TMP/file0
echo __
cat $TMP/file1
## STDOUT: 
i=2
__
file 1
__
file 2
## END
## N-I dash stdout-json: ""
## N-I dash status: 2

#### Redirect in function body AND function call
fun() { echo hi; } 1>&2
fun 2>&1
## stdout-json: "hi\n"
## stderr-json: ""

#### Descriptor redirect with spaces
# Hm this seems like a failure of lookahead!  The second thing should look to a
# file-like thing.
# I think this is a posix issue.
# tag: posix-issue
echo one 1>&2
echo two 1 >&2
echo three 1>& 2
## stderr-json: "one\ntwo 1\nthree\n"

#### Filename redirect with spaces
# This time 1 *is* a descriptor, not a word.  If you add a space between 1 and
# >, it doesn't work.
echo two 1> $TMP/file-redir1.txt
cat $TMP/file-redir1.txt
## stdout: two

#### Quoted filename redirect with spaces
# POSIX makes node of this
echo two \1 > $TMP/file-redir2.txt
cat $TMP/file-redir2.txt
## stdout: two 1

#### Descriptor redirect with filename
# bash/mksh treat this like a filename, not a descriptor.
# dash aborts.
echo one 1>&$TMP/nonexistent-filename__
echo "status=$?"
## stdout: status=1
## BUG bash stdout: status=0
## OK dash stdout-json: ""
## OK dash status: 2

#### redirect for loop
for i in $(seq 3)
do
  echo $i
done > $TMP/redirect-for-loop.txt
cat $TMP/redirect-for-loop.txt
## stdout-json: "1\n2\n3\n"

#### redirect subshell
( echo foo ) 1>&2
## stderr: foo
## stdout-json: ""

#### Prefix redirect for loop -- not allowed
>$TMP/redirect2.txt for i in $(seq 3)
do
  echo $i
done
cat $TMP/redirect2.txt
## status: 2
## OK mksh status: 1

#### Brace group redirect
# Suffix works, but prefix does NOT work.
# That comes from '| compound_command redirect_list' in the grammar!
{ echo block-redirect; } > $TMP/br.txt
cat $TMP/br.txt | wc -c
## stdout: 15

#### Redirect echo to stderr, and then redirect all of stdout somewhere.
{ echo foo 1>&2; echo 012345789; } > $TMP/block-stdout.txt
cat $TMP/block-stdout.txt |  wc -c 
## stderr: foo
## stdout: 10

#### Redirect in the middle of two assignments
FOO=foo >$TMP/out.txt BAR=bar printenv.py FOO BAR
tac $TMP/out.txt
## stdout-json: "bar\nfoo\n"

#### Redirect in the middle of a command
f=$TMP/out
echo -n 1 2 '3 ' > $f
echo -n 4 5 >> $f '6 '
echo -n 7 >> $f 8 '9 '
echo -n >> $f 1 2 '3 '
echo >> $f -n 4 5 '6 '
cat $f
## stdout-json: "1 2 3 4 5 6 7 8 9 1 2 3 4 5 6 "

#### Named file descriptor
exec {myfd}> $TMP/named-fd.txt
echo named-fd-contents >& $myfd
cat $TMP/named-fd.txt
## stdout: named-fd-contents
## status: 0
## N-I dash/mksh stdout-json: ""
## N-I dash/mksh status: 127

#### Double digit fd (20> file)
exec 20> "$TMP/double-digit-fd.txt"
echo hello20 >&20
cat "$TMP/double-digit-fd.txt"
## stdout: hello20
## BUG dash stdout-json: ""
## BUG dash status: 127

#### : 9> fdleak (OSH regression)
true 9> "$TMP/fd.txt"
( echo world >&9 )
cat "$TMP/fd.txt"
## stdout-json: ""

#### : 3>&3 (OSH regression)
: 3>&3
echo hello
## stdout: hello
## BUG mksh stdout-json: ""
## BUG mksh status: 1

#### : 3>&3-
: 3>&3-
echo hello
## stdout: hello
## N-I dash/mksh stdout-json: ""
## N-I mksh status: 1
## N-I dash status: 2

#### 3>&- << EOF (OSH regression: fail to restore fds)
exec 3> "$TMP/fd.txt"
echo hello 3>&- << EOF
EOF
echo world >&3
exec 3>&-  # close
cat "$TMP/fd.txt"
## STDOUT:
hello
world
## END

#### Open file on descriptor 3 and write to it many times

# different than case below because 3 is the likely first FD of open()

exec 3> "$TMP/fd3.txt"
echo hello >&3
echo world >&3
exec 3>&-  # close
cat "$TMP/fd3.txt"
## STDOUT:
hello
world
## END

#### Open file on descriptor 4 and write to it many times

# different than the case above because because 4 isn't the likely first FD

exec 4> "$TMP/fd4.txt"
echo hello >&4
echo world >&4
exec 4>&-  # close
cat "$TMP/fd4.txt"
## STDOUT:
hello
world
## END

#### Redirect function stdout
f() { echo one; echo two; }
f > $TMP/redirect-func.txt
cat $TMP/redirect-func.txt
## stdout-json: "one\ntwo\n"

#### Nested function stdout redirect
# Shows that a stack is necessary.
inner() {
  echo i1
  echo i2
}
outer() {
  echo o1
  inner > $TMP/inner.txt
  echo o2
}
outer > $TMP/outer.txt
cat $TMP/inner.txt
echo --
cat $TMP/outer.txt
## stdout-json: "i1\ni2\n--\no1\no2\n"

#### Redirect to empty string
f=''
echo s > "$f"
echo "result=$?"
set -o errexit
echo s > "$f"
echo DONE
## stdout: result=1
## status: 1
## OK dash stdout: result=2
## OK dash status: 2

#### Redirect to file descriptor that's not open
# Notes:
# - dash doesn't allow file descriptors greater than 9.  (This is a good
#   thing, because the bash chapter in AOSA book mentions that juggling user
#   vs.  system file descriptors is a huge pain.)
# - But somehow running in parallel under spec-runner.sh changes whether
#   descriptor 3 is open.  e.g. 'echo hi 1>&3'.  Possibly because of
#   /usr/bin/time.  The _tmp/spec/*.task.txt file gets corrupted!
# - Oh this is because I use time --output-file.  That opens descriptor 3.  And
#   then time forks the shell script.  The file descriptor table is inherited.
#   - You actually have to set the file descriptor to something.  What do
#   configure and debootstrap too?

# 3/2020 note: file descriptor 9 failed on Travis, so I changed it to 8.  The
# process state isn't necessarly clean.  TODO: Close the descriptor when OSH
# supports it?

echo hi 1>&8
## status: 1
## OK dash status: 2

#### Open descriptor with exec
# What is the point of this?  ./configure scripts and debootstrap use it.
exec 3>&1
echo hi 1>&3
## stdout: hi
## status: 0

#### Open multiple descriptors with exec
# What is the point of this?  ./configure scripts and debootstrap use it.
exec 3>&1
exec 4>&1
echo three 1>&3
echo four 1>&4
## stdout-json: "three\nfour\n"
## status: 0

#### >| to clobber
echo XX >| $TMP/c.txt
set -o noclobber
echo YY >  $TMP/c.txt  # not globber
echo status=$?
cat $TMP/c.txt
echo ZZ >| $TMP/c.txt
cat $TMP/c.txt
## stdout-json: "status=1\nXX\nZZ\n"
## OK dash stdout-json: "status=2\nXX\nZZ\n"

#### &> redirects stdout and stderr
stdout_stderr.py &> $TMP/f.txt
# order is indeterminate
grep STDOUT $TMP/f.txt >/dev/null && echo 'ok'
grep STDERR $TMP/f.txt >/dev/null && echo 'ok'
## STDOUT:
ok
ok
## END
## N-I dash stdout: STDOUT
## N-I dash stderr: STDERR
## N-I dash status: 1

#### 1>&- to close file descriptor
exec 5> "$TMP/f.txt"
echo hello >&5
exec 5>&-
echo world >&5
cat "$TMP/f.txt"
## stdout-json: "hello\n"

#### 1>&2- to move file descriptor
exec 5> "$TMP/f.txt"
echo hello5 >&5
exec 6>&5-
echo world5 >&5
echo world6 >&6
exec 6>&-
cat "$TMP/f.txt"
## stdout-json: "hello5\nworld6\n"
## N-I dash status: 2
## N-I dash stdout-json: ""
## N-I mksh status: 1
## N-I mksh stdout-json: ""

#### 1>&2- (Bash bug: fail to restore closed fd)
exec 7> "$TMP/f.txt"
: 8>&7 7>&-
echo hello >&7
: 8>&7-
echo world >&7
exec 7>&-
cat "$TMP/f.txt"
## status: 2
## stdout-json: ""
## OK mksh status: 1
## BUG bash status: 0
## BUG bash stdout: hello

#### <> for read/write
echo first >$TMP/rw.txt
exec 8<>$TMP/rw.txt
read line <&8
echo line=$line
echo second 1>&8
echo CONTENTS
cat $TMP/rw.txt
## stdout-json: "line=first\nCONTENTS\nfirst\nsecond\n"

#### <> for read/write named pipes
rm -f "$TMP/f.pipe"
mkfifo "$TMP/f.pipe"
exec 8<> "$TMP/f.pipe"
echo first >&8
echo second >&8
read line1 <&8
read line2 <&8
exec 8<&-
echo line1=$line1 line2=$line2
## stdout: line1=first line2=second

#### &>> appends stdout and stderr

# Fix for flaky tests: dash behaves non-deterministically under load!  It
# doesn't implement the behavior anyway so I don't care why.
case $SH in
  *dash)
    exit 1
    ;;
esac

echo "ok" > $TMP/f.txt
stdout_stderr.py &>> $TMP/f.txt
grep ok $TMP/f.txt >/dev/null && echo 'ok'
grep STDOUT $TMP/f.txt >/dev/null && echo 'ok'
grep STDERR $TMP/f.txt >/dev/null && echo 'ok'
## STDOUT:
ok
ok
ok
## END
## N-I dash stdout-json: ""
## N-I dash status: 1

#### exec redirect then various builtins
exec 5>$TMP/log.txt
echo hi >&5
set -o >&5
echo done
## STDOUT:
done
## END

#### >$file touches a file
rm -f myfile
test -f myfile
echo status=$?
>myfile
test -f myfile
echo status=$?
## STDOUT:
status=1
status=0
## END
# regression for OSH
## stderr-json: ""

#### $(< $file) yields the contents of the file

echo FOO > myfile
foo=$(< myfile)
echo $foo
## STDOUT:
FOO
## END
## N-I dash/ash/yash stdout-json: "\n"

#### $(< file) with more statements

# note that it doesn't do this without a command sub!
# It's apparently a special case in bash, mksh, and zsh?
foo=$(echo begin; < myfile)
echo $foo
echo ---

foo=$(< myfile; echo end)
echo $foo
echo ---

foo=$(< myfile; <myfile)
echo $foo
echo ---

## STDOUT:
begin
---
end
---

---
## END
# weird, zsh behaves differently
## OK zsh STDOUT:
begin
FOO
---
FOO
end
---
FOO
FOO
---
## END


#### < file in pipeline and subshell doesn't work
echo FOO > file2

# This only happens in command subs, which is weird
< file2 | tr A-Z a-z
( < file2 )
echo end
## STDOUT:
end
## END

#### 2>&1 with no command
( exit 42 )  # status is reset after this
echo status=$?
2>&1
echo status=$?
## STDOUT:
status=42
status=0
## END
## stderr-json: ""

#### 2&>1 (is it a redirect or is it like a&>1)
2&>1
echo status=$?
## STDOUT:
status=127
## END
## OK mksh/dash STDOUT:
status=0
## END

#### can't mention big file descriptor
echo hi 9>&1
# 23 is the max descriptor fo rmksh
#echo hi 24>&1
echo hi 99>&1
echo hi 100>&1
## OK osh STDOUT:
hi
hi
hi 100
## END
## STDOUT:
hi
hi 99
hi 100
## END
## BUG bash STDOUT:
hi
hi
hi
## END

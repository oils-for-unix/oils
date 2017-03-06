#!/bin/bash

### Leading redirect
echo hello >tests/hello.txt  # temporary fix
<tests/hello.txt cat
# stdout: hello

### No command
# Hm this is valid in bash and dash.  It's parsed as an assigment with a
# redirect, which doesn't make sense.  But it's a mistake, and should be a W2
# warning for us.
FOO=bar 2>/dev/null

### Redirect in subshell
FOO=$(echo foo 1>&2)
echo $FOO
# stdout:
# stderr: foo

### Redirect in assignment
# dash captures stderr to a file here, which seems correct.  Bash doesn't and
# just lets it go to actual stderr.
# For now we've settled on bash behavior, for compatibility?
FOO=$(echo foo 1>&2) 2>$TMP/no-command.txt
echo FILE=
cat $TMP/no-command.txt
echo "FOO=$FOO"
# OK dash/mksh stdout-json: "FILE=\nfoo\nFOO=\n"
# stdout-json: "FILE=\nFOO=\n"

### Redirect in function body.
# Wow this is interesting, didn't know about it.
func() { echo hi; } 1>&2; func
# stderr: hi

### Descriptor redirect with spaces
# Hm this seems like a failure of lookahead!  The second thing should look to a
# file-like thing.
# I think this is a posix issue.
# tag: posix-issue
echo one 1>&2
echo two 1 >&2
echo three 1>& 2
# stderr-json: "one\ntwo 1\nthree\n"

### Filename redirect with spaces
# This time 1 *is* a descriptor, not a word.  If you add a space between 1 and
# >, it doesn't work.
echo two 1> $TMP/file-redir1.txt
cat $TMP/file-redir1.txt
# stdout: two

### Quoted filename redirect with spaces
# POSIX makes node of this
echo two \1 > $TMP/file-redir2.txt
cat $TMP/file-redir2.txt
# stdout: two 1

### Descriptor redirect with filename
# Should be a syntax error, but bash allows this.
echo one 1>&$TMP/nonexistent-filename__
# status: 2
# stdout-json: ""
# OK  mksh status: 1
# BUG bash status: 0

### redirect for loop
for i in $(seq 3)
do
  echo $i
done > $TMP/redirect-for-loop.txt
cat $TMP/redirect-for-loop.txt
# stdout-json: "1\n2\n3\n"

### Prefix redirect for loop -- not allowed
>$TMP/redirect2.txt for i in $(seq 3)
do
  echo $i
done
cat $TMP/redirect2.txt
# status: 2
# OK mksh status: 1

### Block redirect
# Suffix works, but prefix does NOT work.
# That comes from '| compound_command redirect_list' in the grammar!
{ echo block-redirect; } > $TMP/br.txt
cat $TMP/br.txt | wc -c
# stdout: 15

### Redirect echo to stderr, and then redirect all of stdout somewhere.
{ echo foo 1>&2; echo 012345789; } > $TMP/block-stdout.txt
cat $TMP/block-stdout.txt |  wc -c 
# stderr: foo
# stdout: 10

### Redirect in the middle of two assignments
FOO=foo >$TMP/out.txt BAR=bar printenv.py FOO BAR
tac $TMP/out.txt
# stdout-json: "bar\nfoo\n"

### Redirect in the middle of a command
f=$TMP/out
echo -n 1 2 '3 ' > $f
echo -n 4 5 >> $f '6 '
echo -n 7 >> $f 8 '9 '
echo -n >> $f 1 2 '3 '
echo >> $f -n 4 5 '6 '
cat $f
# stdout-json: "1 2 3 4 5 6 7 8 9 1 2 3 4 5 6 "

### Named file descriptor
exec {myfd}> $TMP/named-fd.txt
echo named-fd-contents >& $myfd
cat $TMP/named-fd.txt
# stdout: named-fd-contents
# N-I dash/mksh stdout-json: ""




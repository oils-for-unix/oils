#!/bin/bash

### case
foo=a; case $foo in [0-9]) echo number;; [a-z]) echo letter;; esac
# stdout: letter

### case in subshell
# Hm this subhell has to know about the closing ) and stuff like that.
# case_clause is a compound_command, which is a command.  And a subshell
# takes a compound_list, which is a list of terms, which has and_ors in them
# ... which eventually boils down to a command.
echo $(foo=a; case $foo in [0-9]) echo number;; [a-z]) echo letter;; esac)
# stdout: letter

### Command sub word part
# "The token shall not be delimited by the end of the substitution."
foo=FOO; echo $(echo $foo)bar$(echo $foo)
# stdout: FOObarFOO

### Backtick
foo=FOO; echo `echo $foo`bar`echo $foo`
# stdout: FOObarFOO

### Backtick 2
echo `echo -n l; echo -n s`
# stdout: ls

### Nested backticks
# Inner `` are escaped!  # Not sure how to do triple..  Seems like an unlikely
# use case.  Not sure if I even want to support this!
echo X > $TMP/000000-first
echo `\`echo -n l; echo -n s\` $TMP | head -n 1`
# stdout: 000000-first

### Making command out of command sub should work
# Works in bash and dash!
$(echo ec)$(echo ho) split builtin
# stdout: split builtin

### Making keyword out of command sub should NOT work
# This doesn't work in bash or dash!  Hm builtins are different than keywords /
# reserved words I guess.
# dash fails, but gives code 0
$(echo f)$(echo or) i in a b c; do echo $i; done
echo status=$?
# stdout-json: ""
# status: 2
# BUG dash stdout-json: "\nstatus=0\n"
# BUG dash status: 0
# OK mksh status: 1

### Command sub with here doc
echo $(<<EOF tac
one
two
EOF
)
# stdout: two one

### Here doc with pipeline
<<EOF tac | tr '\n' 'X'
one
two
EOF
# stdout-json: "twoXoneX"

### Command Sub word split
argv.py $(echo 'hi there') "$(echo 'hi there')"
# stdout: ['hi', 'there', 'hi there']

### Command Sub trailing newline removed
s=$(python -c 'print "ab\ncd\n"')
argv "$s"
# stdout: ['ab\ncd']

### Command Sub trailing whitespace not removed
s=$(python -c 'print "ab\ncd\n "')
argv "$s"
# stdout: ['ab\ncd\n ']

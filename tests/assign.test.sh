#!/bin/bash

### Env value doesn't persist
FOO=foo printenv.py FOO
echo [$FOO]
# stdout-json: "foo\n[]\n"

### Env value with equals
FOO=foo=foo printenv.py FOO
# stdout: foo=foo

### Env value using preceding Env binding
# This means that for ASSIGNMENT_WORD, on the RHS you invoke the parser again!
# Could be any kind of quoted string.
FOO="foo" BAR="[$FOO]" printenv.py FOO BAR
# stdout-json: "foo\n[foo]\n"
# BUG mksh stdout-json: "foo\n[]\n"

### Env value with two quotes
FOO='foo'"adjacent" printenv.py FOO
# stdout: fooadjacent

### Env value with escaped <
FOO=foo\<foo printenv.py FOO
# stdout: foo<foo

### Escaped = in command name
# foo=bar is in the 'tests' dir.
PATH=tests foo\=bar
# stdout: HI

### Env binding not allowed before compound command
# bash gives exit code 2 for syntax error, because of 'do'.
# dash gives 0 because there is stuff after for?  Should really give an error.
# mksh gives acceptable error of 1.
FOO=bar for i in a b; do printenv.py $FOO; done
# BUG dash status: 0
# OK  mksh status: 1
# status: 2

### Trying to run keyword 'for'
FOO=bar for
# status: 127

### Empty env binding
EMPTY= printenv.py EMPTY
# stdout:

### Assignment doesn't do word splitting
words='one two'
a=$words
argv.py "$a"
# stdout: ['one two']

### Assignment doesn't do glob expansion
touch _tmp/z.Z _tmp/zz.Z
a=_tmp/*.Z
argv.py "$a"
# stdout: ['_tmp/*.Z']

### Env binding in readonly/declare disallowed
# I'm disallowing this in the oil shell, because it doesn't work in bash!
# (v=None vs v=foo)
# assert status 2 for parse error, but allow stdout v=None/status 0 for
# existing implementations.
FOO=foo readonly v=$(printenv.py FOO)
echo "v=$v"
# OK bash/dash/mksh stdout: v=None
# OK bash/dash/mksh status: 0
# status: 2

### Dependent export setting
# FOO is not respected here either.
export FOO=foo v=$(printenv.py FOO)
echo "v=$v"
# stdout: v=None

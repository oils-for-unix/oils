#!/bin/bash
#
# Bash implements type -t.
# 
# NOTE: Aliases don't work in batch mode!  Interactive only.

#### type -t builtin -> function
f() { echo hi; }
type -t f
## stdout-json: "function\n"

#### type -t builtin -> builtin
type -t echo read : [ declare local break continue
## stdout-json: "builtin\nbuiltin\nbuiltin\nbuiltin\nbuiltin\nbuiltin\nbuiltin\nbuiltin\n"

#### type -t builtin -> keyword
type -t for time ! fi do {
## stdout-json: "keyword\nkeyword\nkeyword\nkeyword\nkeyword\nkeyword\n"

#### type -t builtin -> file
type -t find xargs
## stdout-json: "file\nfile\n"

#### type -t builtin -> not found
type -t echo ZZZ find =
echo status=$?
## stdout-json: "builtin\nfile\nstatus=1\n"

#### help
help
help help
## status: 0

#### bad help topic
help ZZZ 2>$TMP/err.txt
echo "help=$?"
cat $TMP/err.txt | grep -i 'no help topics' >/dev/null
echo "grep=$?"
## stdout-json: "help=1\ngrep=0\n"

#### type -p builtin -> file
type -p mv tar grep
## STDOUT:
/bin/mv
/bin/tar
/bin/grep
## END

#### type -p builtin -> not found
type -p FOO BAR NOT_FOUND
## status: 1
## stdout-json: ""

#### type -p builtin -> not a file
type -p cd type builtin command
## stdout-json: ""

#### type -P builtin -> file
type -P mv tar grep
## STDOUT:
/bin/mv
/bin/tar
/bin/grep
## END

#### type -P builtin -> not found
type -P FOO BAR NOT_FOUND
## status: 1
## stdout-json: ""

#### type -P builtin -> not a file
type -P cd type builtin command
## stdout-json: ""
## status: 1

#### type -P builtin -> not a file but file found
mv () { ls; }
tar () { ls; }
grep () { ls; }
type -P mv tar grep cd builtin command type
## status: 1
## STDOUT:
/bin/mv
/bin/tar
/bin/grep
## END

#### type -f builtin -> not found
type -f FOO BAR NOT FOUND
## status: 1

#### type -f builtin -> function and file exists
mv () { ls; }
tar () { ls; }
grep () { ls; }
type -f mv tar grep
## STDOUT:
/bin/mv is a file
/bin/tar is a file
/bin/grep is a file
## OK bash STDOUT:
mv is /bin/mv
tar is /bin/tar
grep is /bin/grep

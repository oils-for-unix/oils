#!/bin/bash
#
# Bash implements type -t.
# 
# NOTE: Aliases don't work in batch mode!  Interactive only.

### type -t builtin -> function
f() { echo hi; }
type -t f
# stdout-json: "function\n"

### type -t builtin -> builtin
type -t echo read : [ declare local break continue
# stdout-json: "builtin\nbuiltin\nbuiltin\nbuiltin\nbuiltin\nbuiltin\nbuiltin\nbuiltin\n"

### type -t builtin -> keyword
type -t for time ! fi do {
# stdout-json: "keyword\nkeyword\nkeyword\nkeyword\nkeyword\nkeyword\n"

### type -t builtin -> file
type -t find xargs
# stdout-json: "file\nfile\n"

### type -t builtin -> not found
type -t echo ZZZ find =
echo status=$?
# stdout-json: "builtin\nfile\nstatus=1\n"

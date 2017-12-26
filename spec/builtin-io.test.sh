#!/bin/bash
#
# echo, read
# later: perhaps mapfile, etc.

### echo dashes
echo -
echo --
echo ---
# stdout-json: "-\n--\n---\n"

### echo -en
echo -en 'abc\ndef\n'
# stdout-json: "abc\ndef\n"
# N-I dash stdout-json: "-en abc\ndef\n\n"

### echo -ez (invalid flag)
# bash differs from the other two shells, but its behavior is possibly more
# sensible, if you're going to ignore the error.  It doesn't make sense for the
# 'e' to mean 2 different things simultaneously: flag and literal to be
# printed.
echo -ez 'abc\n'
# stdout-json: "-ez abc\\n\n"
# BUG dash/mksh stdout-json: "-ez abc\n\n"

### Read builtin
# NOTE: there are TABS below
read x <<EOF
A		B C D E
FG
EOF
echo "[$x]"
# stdout: [A		B C D E]
# status: 0

### Read builtin with no newline.
# This is odd because the variable is populated successfully.  OSH/Oil might
# need a separate put reading feature that doesn't use IFS.
echo -n ZZZ | { read x; echo $?; echo $x; }
# stdout-json: "1\nZZZ\n"
# status: 0

### Read builtin with multiple variables
# NOTE: there are TABS below
read x y z <<EOF
A		B C D E
FG
EOF
echo "$x/$y/$z"
# stdout: A/B/C D E
# status: 0

### Read builtin with not enough variables
set -o errexit
set -o nounset  # hm this doesn't change it
read x y z <<EOF
A B
EOF
echo /$x/$y/$z/
# stdout: /A/B//
# status: 0

### get umask
umask | grep '[0-9]\+'  # check for digits
# status: 0

### Read -n (with $REPLY)
echo 12345 > $TMP/readn.txt
read -n 4 x < $TMP/readn.txt
read -n 2 < $TMP/readn.txt  # Do it again with no variable
argv.py $x $REPLY
# stdout: ['1234', '12']
# N-I dash stdout: []

### read -r ignores backslashes
echo 'one\ two' > $TMP/readr.txt
read escaped < $TMP/readr.txt
read -r raw < $TMP/readr.txt
argv "$escaped" "$raw"
# stdout: ['one two', 'one\\ two']


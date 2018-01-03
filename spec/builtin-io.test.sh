#!/bin/bash
#
# echo, read
# later: perhaps mapfile, etc.

### echo dashes
echo -
echo --
echo ---
# stdout-json: "-\n--\n---\n"
# BUG zsh stdout-json: "\n--\n---\n"

### echo -en
echo -en 'abc\ndef\n'
# stdout-json: "abc\ndef\n"
# N-I dash stdout-json: "-en abc\ndef\n\n"

### echo -ez (invalid flag)
# bash differs from the other three shells, but its behavior is possibly more
# sensible, if you're going to ignore the error.  It doesn't make sense for
# the 'e' to mean 2 different things simultaneously: flag and literal to be
# printed.
echo -ez 'abc\n'
# stdout-json: "-ez abc\\n\n"
# OK dash/mksh/zsh stdout-json: "-ez abc\n\n"

### echo -e with C escapes
# https://www.gnu.org/software/bash/manual/bashref.html#Bourne-Shell-Builtins
# not sure why \c is like NUL?
# zsh doesn't allow \E for some reason.
echo -e '\a\b\d\e\f'
# stdout-json: "\u0007\u0008\\d\u001b\u000c\n"
# N-I dash stdout-json: "-e \u0007\u0008\\d\\e\u000c\n"

### echo -e with whitespace C escapes
echo -e '\n\r\t\v'
# stdout-json: "\n\r\t\u000b\n"
# N-I dash stdout-json: "-e \n\r\t\u000b\n"

### \0
echo -e 'ab\0cd'
# stdout-json: "ab\u0000cd\n"
# dash truncates it
# BUG dash stdout-json: "-e ab\n"

### \c stops processing input
echo -e xy  'ab\cde'  'ab\cde'
# stdout-json: "xy ab"
# OK dash stdout-json: "-e xy ab"
# N-I mksh stdout-json: "xy abde abde"

### echo -e with hex escape
echo -e 'abcd\x65f'
# stdout-json: "abcdef\n"
# N-I dash stdout-json: "-e abcd\\x65f\n"

### echo -e with octal escape
echo -e 'abcd\044e'
# stdout-json: "abcd$e\n"
# OK dash stdout-json: "-e abcd$e\n"

### echo -e with 4 digit unicode escape
echo -e 'abcd\u0065f'
# stdout-json: "abcdef\n"
# OK dash stdout-json: "-e abcd\\u0065f\n"

### echo -e with 8 digit unicode escape
echo -e 'abcd\U00000065f'
# stdout-json: "abcdef\n"
# OK dash stdout-json: "-e abcd\\U00000065f\n"

### \0377 is the highest octal byte
echo -en '\03777' | od -A n -t x1 | sed 's/ \+/ /g'
# stdout-json: " ff 37\n"
# N-I dash stdout-json: " 2d 65 6e 20 ff 37 0a\n"

### \0400 is one more than the highest octal byte
# It is 256 % 256 which gets interpreted as a NUL byte.
echo -en '\04000' | od -A n -t x1 | sed 's/ \+/ /g'
# stdout-json: " 00 30\n"
# N-I dash stdout-json: " 2d 65 6e 20\n"

### \0777 is out of range
echo -en '\0777' | od -A n -t x1 | sed 's/ \+/ /g'
# stdout-json: " ff\n"
# OK mksh stdout-json: " c3 bf\n"
# OK dash stdout-json: " 2d 65 6e 20 ff 0a\n"

### incomplete hex escape
echo -en 'abcd\x6' | od -A n -c | sed 's/ \+/ /g'
# stdout-json: " a b c d 006\n"
# N-I dash stdout-json: " - e n a b c d \\ x 6 \\n\n"

### \x
# I consider mksh and zsh a bug because \x is not an escape
echo -e '\x' '\xg' | od -A n -c | sed 's/ \+/ /g'
# stdout-json: " \\ x \\ x g \\n\n"
# N-I dash stdout-json: " - e \\ x \\ x g \\n\n"
# BUG mksh/zsh stdout-json: " \\0 \\0 g \\n\n"

### incomplete octal escape
echo -en 'abcd\04' | od -A n -c | sed 's/ \+/ /g'
# stdout-json: " a b c d 004\n"
# OK dash stdout-json: " - e n a b c d 004 \\n\n"

### incomplete unicode escape
echo -en 'abcd\u006' | od -A n -c | sed 's/ \+/ /g'
# stdout-json: " a b c d 006\n"
# N-I dash stdout-json: " - e n a b c d \\ u 0 0 6 \\n\n"

### \u6
echo -e '\u6' | od -A n -c | sed 's/ \+/ /g'
# stdout-json: " 006 \\n\n"
# N-I dash stdout-json: " - e \\ u 6 \\n\n"

### \0 \1 \8
# \0 is special, but \1 isn't in bash
# \1 is special in dash!  geez
echo -e '\0' '\1' '\8' | od -A n -c | sed 's/ \+/ /g'
# stdout-json: " \\0 \\ 1 \\ 8 \\n\n"
# BUG dash stdout-json: " - e 001 \\ 8 \\n\n"

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

### Read -n (with $REPLY)
echo 12345 > $TMP/readn.txt
read -n 4 x < $TMP/readn.txt
read -n 2 < $TMP/readn.txt  # Do it again with no variable
argv.py $x $REPLY
# stdout: ['1234', '12']
# N-I dash/zsh stdout: []

### read -r ignores backslashes
echo 'one\ two' > $TMP/readr.txt
read escaped < $TMP/readr.txt
read -r raw < $TMP/readr.txt
argv "$escaped" "$raw"
# stdout: ['one two', 'one\\ two']

### read -r with other backslash escapes
echo 'one\ two\x65three' > $TMP/readr.txt
read escaped < $TMP/readr.txt
read -r raw < $TMP/readr.txt
argv "$escaped" "$raw"
# mksh respects the hex escapes here, but other shells don't!
# stdout: ['one twox65three', 'one\\ two\\x65three']
# BUG mksh/zsh stdout: ['one twoethree', 'one\\ twoethree']

### read with line continuation reads multiple physical lines
echo -e 'one\\\ntwo\n' > $TMP/readr.txt
read escaped < $TMP/readr.txt
read -r raw < $TMP/readr.txt
argv "$escaped" "$raw"
# stdout: ['onetwo', 'one\\']
# N-I dash stdout: ['-e onetwo', '-e one\\']

### read -r with \n
echo '\nline' > $TMP/readr.txt
read escaped < $TMP/readr.txt
read -r raw < $TMP/readr.txt
argv "$escaped" "$raw"
# dash/mksh/zsh are bugs because at least the raw mode should let you read a
# literal \n.
# stdout: ['nline', '\\nline']
# BUG dash/mksh/zsh stdout: ['', '']

### Read with IFS=$'\n'
# The leading spaces are stripped if they appear in IFS.
IFS=$(echo -e '\n')
read var <<EOF
  a b c
  d e f
EOF
echo "[$var]"
# stdout: [  a b c]
# N-I dash stdout: [a b c]

### Read with IFS=:
# The leading spaces are stripped if they appear in IFS.
# IFS chars are escaped with :.
IFS=:
{ echo '  \\a :b\: c:d\';
  echo '  e'
} > $TMP/read-ifs.txt
read a b c d < $TMP/read-ifs.txt
echo "[$a|$b|$c|$d]"
# stdout: [  a |b: c|d  e|]
# BUG bash stdout: [  \a |b: c|d  e|]

### Read with IFS=''
IFS=''
read x y <<EOF
  a b c d
EOF
echo "[$x|$y]"
# stdout: [  a b c d|]

### Read should not respect C escapes.
# bash doesn't respect these, but other shells do.  Gah!  I think bash
# behavior makes more sense.  It only escapes IFS.
echo '\a \b \c \d \e \f \g \h \x65 \145 \i' > $TMP/read-c.txt
read line < $TMP/read-c.txt
echo $line
# stdout-json: "a b c d e f g h x65 145 i\n"
# BUG dash/zsh stdout-json: "\u0007 \u0008\n"
# BUG mksh stdout-json: "\u0007 \u0008 d \u001b \u000c g h e 145 i\n"


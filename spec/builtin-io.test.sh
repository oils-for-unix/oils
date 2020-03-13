#!/bin/bash
#
# echo, read
# later: perhaps mapfile, etc.

#### echo dashes
echo -
echo --
echo ---
## stdout-json: "-\n--\n---\n"
## BUG zsh stdout-json: "\n--\n---\n"

#### echo backslashes
echo \\
echo '\'
echo '\\'
echo "\\"
## STDOUT:
\
\
\\
\
## BUG dash/mksh/zsh STDOUT:
\
\
\
\
## END

#### echo -e backslashes
echo -e \\
echo -e '\'
echo -e '\\'
echo -e "\\"
## STDOUT:
\
\
\
\
## N-I dash STDOUT:
-e \
-e \
-e \
-e \
## END

#### echo -en
echo -en 'abc\ndef\n'
## stdout-json: "abc\ndef\n"
## N-I dash stdout-json: "-en abc\ndef\n\n"

#### echo -ez (invalid flag)
# bash differs from the other three shells, but its behavior is possibly more
# sensible, if you're going to ignore the error.  It doesn't make sense for
# the 'e' to mean 2 different things simultaneously: flag and literal to be
# printed.
echo -ez 'abc\n'
## stdout-json: "-ez abc\\n\n"
## OK dash/mksh/zsh stdout-json: "-ez abc\n\n"

#### echo -e with embedded newline 
flags='-e'
case $SH in dash) flags='' ;; esac

echo $flags 'foo
bar'
## STDOUT:
foo
bar
## END

#### echo -e line continuation
flags='-e'
case $SH in dash) flags='' ;; esac

echo $flags 'foo\
bar'
## STDOUT:
foo\
bar
## END

#### echo -e with C escapes
# https://www.gnu.org/software/bash/manual/bashref.html#Bourne-Shell-Builtins
# not sure why \c is like NUL?
# zsh doesn't allow \E for some reason.
echo -e '\a\b\d\e\f'
## stdout-json: "\u0007\u0008\\d\u001b\u000c\n"
## N-I dash stdout-json: "-e \u0007\u0008\\d\\e\u000c\n"

#### echo -e with whitespace C escapes
echo -e '\n\r\t\v'
## stdout-json: "\n\r\t\u000b\n"
## N-I dash stdout-json: "-e \n\r\t\u000b\n"

#### \0
echo -e 'ab\0cd'
## stdout-json: "ab\u0000cd\n"
# dash truncates it
## BUG dash stdout-json: "-e ab\n"

#### \c stops processing input
flags='-e'
case $SH in dash) flags='' ;; esac

echo $flags xy  'ab\cde'  'ab\cde'
## stdout-json: "xy ab"
## N-I mksh stdout-json: "xy abde abde"

#### echo -e with hex escape
echo -e 'abcd\x65f'
## stdout-json: "abcdef\n"
## N-I dash stdout-json: "-e abcd\\x65f\n"

#### echo -e with octal escape
flags='-e'
case $SH in dash) flags='' ;; esac

echo $flags 'abcd\044e'
## stdout-json: "abcd$e\n"

#### echo -e with 4 digit unicode escape
flags='-e'
case $SH in dash) flags='' ;; esac

echo $flags 'abcd\u0065f'
## STDOUT:
abcdef
## END
## N-I dash/ash stdout-json: "abcd\\u0065f\n"

#### echo -e with 8 digit unicode escape
flags='-e'
case $SH in dash) flags='' ;; esac

echo $flags 'abcd\U00000065f'
## STDOUT:
abcdef
## END
## N-I dash/ash stdout-json: "abcd\\U00000065f\n"

#### \0377 is the highest octal byte
echo -en '\03777' | od -A n -t x1 | sed 's/ \+/ /g'
## stdout-json: " ff 37\n"
## N-I dash stdout-json: " 2d 65 6e 20 ff 37 0a\n"

#### \0400 is one more than the highest octal byte
# It is 256 % 256 which gets interpreted as a NUL byte.
echo -en '\04000' | od -A n -t x1 | sed 's/ \+/ /g'
## stdout-json: " 00 30\n"
## BUG ash stdout-json: " 20 30 30\n"
## N-I dash stdout-json: " 2d 65 6e 20\n"

#### \0777 is out of range
flags='-en'
case $SH in dash) flags='-n' ;; esac

echo $flags '\0777' | od -A n -t x1 | sed 's/ \+/ /g'
## stdout-json: " ff\n"
## BUG mksh stdout-json: " c3 bf\n"
## BUG ash stdout-json: " 3f 37\n"

#### incomplete hex escape
echo -en 'abcd\x6' | od -A n -c | sed 's/ \+/ /g'
## stdout-json: " a b c d 006\n"
## N-I dash stdout-json: " - e n a b c d \\ x 6 \\n\n"

#### \x
# I consider mksh and zsh a bug because \x is not an escape
echo -e '\x' '\xg' | od -A n -c | sed 's/ \+/ /g'
## stdout-json: " \\ x \\ x g \\n\n"
## N-I dash stdout-json: " - e \\ x \\ x g \\n\n"
## BUG mksh/zsh stdout-json: " \\0 \\0 g \\n\n"

#### incomplete octal escape
flags='-en'
case $SH in dash) flags='-n' ;; esac

echo $flags 'abcd\04' | od -A n -c | sed 's/ \+/ /g'
## stdout-json: " a b c d 004\n"

#### incomplete unicode escape
echo -en 'abcd\u006' | od -A n -c | sed 's/ \+/ /g'
## stdout-json: " a b c d 006\n"
## N-I dash stdout-json: " - e n a b c d \\ u 0 0 6 \\n\n"
## BUG ash stdout-json: " a b c d \\ u 0 0 6\n"

#### \u6
flags='-en'
case $SH in dash) flags='-n' ;; esac

echo $flags '\u6' | od -A n -c | sed 's/ \+/ /g'
## stdout-json: " 006\n"
## N-I dash/ash stdout-json: " \\ u 6\n"

#### \0 \1 \8
# \0 is special, but \1 isn't in bash
# \1 is special in dash!  geez
flags='-en'
case $SH in dash) flags='-n' ;; esac

echo $flags '\0' '\1' '\8' | od -A n -c | sed 's/ \+/ /g'
## stdout-json: " \\0 \\ 1 \\ 8\n"
## BUG dash stdout-json: " 001 \\ 8\n"
## BUG ash stdout-json: " \\0 001 \\ 8\n"

#### Read builtin
# NOTE: there are TABS below
read x <<EOF
A		B C D E
FG
EOF
echo "[$x]"
## stdout: [A		B C D E]
## status: 0

#### Read from empty file
echo -n '' > $TMP/empty.txt
read x < $TMP/empty.txt
argv.py "status=$?" "$x"
## stdout: ['status=1', '']
## status: 0

#### Read builtin with no newline.
# This is odd because the variable is populated successfully.  OSH/Oil might
# need a separate put reading feature that doesn't use IFS.
echo -n ZZZ | { read x; echo $?; echo $x; }
## stdout-json: "1\nZZZ\n"
## status: 0

#### Read builtin with multiple variables
# NOTE: there are TABS below
read x y z <<EOF
A		B C D E 
FG
EOF
echo "[$x/$y/$z]"
## stdout: [A/B/C D E]
## BUG dash stdout: [A/B/C D E ]
## status: 0

#### Read builtin with not enough variables
set -o errexit
set -o nounset  # hm this doesn't change it
read x y z <<EOF
A B
EOF
echo /$x/$y/$z/
## stdout: /A/B//
## status: 0

#### Read -n (with $REPLY)
echo 12345 > $TMP/readn.txt
read -n 4 x < $TMP/readn.txt
read -n 2 < $TMP/readn.txt  # Do it again with no variable
argv.py $x $REPLY
## stdout: ['1234', '12']
## N-I dash/zsh stdout: []

#### Read uses $REPLY (without -n)
echo 123 > $TMP/readreply.txt
read < $TMP/readreply.txt
echo $REPLY
## stdout: 123
## N-I dash stdout:

#### read -r ignores backslashes
echo 'one\ two' > $TMP/readr.txt
read escaped < $TMP/readr.txt
read -r raw < $TMP/readr.txt
argv.py "$escaped" "$raw"
## stdout: ['one two', 'one\\ two']

#### read -r with other backslash escapes
echo 'one\ two\x65three' > $TMP/readr.txt
read escaped < $TMP/readr.txt
read -r raw < $TMP/readr.txt
argv.py "$escaped" "$raw"
# mksh respects the hex escapes here, but other shells don't!
## stdout: ['one twox65three', 'one\\ two\\x65three']
## BUG mksh/zsh stdout: ['one twoethree', 'one\\ twoethree']

#### read with line continuation reads multiple physical lines
# NOTE: osh failing because of file descriptor issue.  stdin has to be closed!
tmp=$TMP/$(basename $SH)-readr.txt
echo -e 'one\\\ntwo\n' > $tmp
read escaped < $tmp
read -r raw < $tmp
argv.py "$escaped" "$raw"
## stdout: ['onetwo', 'one\\']
## N-I dash stdout: ['-e onetwo', '-e one\\']

#### read multiple vars spanning many lines
read x y << 'EOF'
one-\
two three-\
four five-\
six
EOF
argv.py "$x" "$y" "$z"
## stdout: ['one-two', 'three-four five-six', '']

#### read -r with \n
echo '\nline' > $TMP/readr.txt
read escaped < $TMP/readr.txt
read -r raw < $TMP/readr.txt
argv.py "$escaped" "$raw"
# dash/mksh/zsh are bugs because at least the raw mode should let you read a
# literal \n.
## stdout: ['nline', '\\nline']
## BUG dash/mksh/zsh stdout: ['', '']

#### Read with IFS=$'\n'
# The leading spaces are stripped if they appear in IFS.
IFS=$(echo -e '\n')
read var <<EOF
  a b c
  d e f
EOF
echo "[$var]"
## stdout: [  a b c]
## N-I dash stdout: [a b c]

#### Read multiple lines with IFS=:
# The leading spaces are stripped if they appear in IFS.
# IFS chars are escaped with :.
tmp=$TMP/$(basename $SH)-read-ifs.txt
IFS=:
cat >$tmp <<'EOF'
  \\a :b\: c:d\
  e
EOF
read a b c d < $tmp
# Use printf because echo in dash/mksh interprets escapes, while it doesn't in
# bash.
printf "%s\n" "[$a|$b|$c|$d]"
## stdout: [  \a |b: c|d  e|]

#### Read with IFS=''
IFS=''
read x y <<EOF
  a b c d
EOF
echo "[$x|$y]"
## stdout: [  a b c d|]

#### Read should not respect C escapes.
# bash doesn't respect these, but other shells do.  Gah!  I think bash
# behavior makes more sense.  It only escapes IFS.
echo '\a \b \c \d \e \f \g \h \x65 \145 \i' > $TMP/read-c.txt
read line < $TMP/read-c.txt
echo $line
## stdout-json: "a b c d e f g h x65 145 i\n"
## BUG ash stdout-json: "abcdefghx65 145 i\n"
## BUG dash/zsh stdout-json: "\u0007 \u0008\n"
## BUG mksh stdout-json: "\u0007 \u0008 d \u001b \u000c g h e 145 i\n"

#### Read builtin uses dynamic scope
f() {
  read head << EOF
ref: refs/heads/dev/andy
EOF
}
f
echo $head
## STDOUT:
ref: refs/heads/dev/andy
## END

#### read -a reads into array

# read -a is used in bash-completion
# none of these shells implement it
case $SH in
  *mksh|*dash|*zsh|*/ash)
    exit 2;
    ;;
esac

read -a myarray <<'EOF'
a b c\ d
EOF
argv.py "${myarray[@]}"

# arguments are ignored here
read -r -a array2 extra arguments <<'EOF'
a b c\ d
EOF
argv.py "${array2[@]}"
argv.py "${extra[@]}"
argv.py "${arguments[@]}"
## status: 0
## STDOUT:
['a', 'b', 'c d']
['a', 'b', 'c\\', 'd']
[]
[]
## END
## N-I dash/mksh/zsh/ash status: 2
## N-I dash/mksh/zsh/ash stdout-json: ""

#### read -n with invalid arg
read -n not_a_number
echo status=$?
## stdout: status=2
## OK bash stdout: status=1
## N-I zsh stdout-json: ""

#### read returns correct number of bytes without EOF
case $SH in
  *bash|*osh) FLAG=n ;;
  *mksh)      FLAG=N ;;
  *) exit ;;  # other shells don't implement it, or hang
esac

i=0
while true; do
  echo -n x

  (( i++ ))

  # TODO: Why does OSH hang without this test?  Other shells are fine.  I can't
  # reproduce outside of sh_spec.py.
  if test $i = 100; then
    break
    #true
  fi
done | { read -$FLAG 3; echo $REPLY; }

## status: 0
## stdout: xxx
## N-I dash/ash stdout-json: ""

# zsh appears to hang with -k
## N-I zsh stdout-json: ""

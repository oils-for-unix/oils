#
# echo, read, mapfile
# TODO mapfile options: -c, -C, -u, etc.

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
## N-I dash stdout-json: "-e ab\u0000cd\n"

#### \c stops processing input
flags='-e'
case $SH in dash) flags='' ;; esac

echo $flags xy  'ab\cde'  'zzz'
## stdout-json: "xy ab"
## N-I mksh stdout-json: "xy abde zzz"

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
## N-I dash stdout-json: " 2d 65 6e 20 00 30 0a\n"

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
## BUG dash/ash stdout-json: " \\0 001 \\ 8\n"

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

# No variable name, behaves the same
read < $TMP/empty.txt
argv.py "status=$?" "$REPLY"

## STDOUT:
['status=1', '']
['status=1', '']
## END
## OK dash STDOUT:
['status=1', '']
['status=2', '']
## END
## status: 0

#### read /dev/null
read -n 1 </dev/null
echo $?
## STDOUT:
1
## END
## OK dash stdout: 2

#### read with zero args
echo | read
echo status=$?
## STDOUT:
status=0
## END
## BUG dash STDOUT:
status=2
## END

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

#### IFS= read -n (OSH regression: value saved in tempenv)
echo XYZ > "$TMP/readn.txt"
IFS= TMOUT= read -n 1 char < "$TMP/readn.txt"
argv.py "$char"
## stdout: ['X']
## N-I dash/zsh stdout: ['']

#### read -n with invalid arg
read -n not_a_number
echo status=$?
## stdout: status=2
## OK bash stdout: status=1
## N-I zsh stdout-json: ""

#### read -n from pipe
case $SH in (dash|ash|zsh) exit ;; esac

echo abcxyz | { read -n 3; echo reply=$REPLY; }
## status: 0
## stdout: reply=abc
## N-I dash/ash/zsh stdout-json: ""

# zsh appears to hang with -k
## N-I zsh stdout-json: ""

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

#### read -s from pipe, not a terminal
case $SH in (dash|zsh) exit ;; esac

# It's hard to really test this because it requires a terminal.  We hit a
# different code path when reading through a pipe.  There can be bugs there
# too!

echo foo | { read -s; echo $REPLY; }
echo bar | { read -n 2 -s; echo $REPLY; }

# Hm no exit 1 here?  Weird
echo b | { read -n 2 -s; echo $?; echo $REPLY; }
## STDOUT:
foo
ba
0
b
## END
## N-I dash/zsh stdout-json: ""

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

#### read -d : (colon-separated records)
printf a,b,c:d,e,f:g,h,i | {
  IFS=,
  read -d : v1
  echo "v1=$v1"
  read -d : v1 v2
  echo "v1=$v1 v2=$v2"
  read -d : v1 v2 v3
  echo "v1=$v1 v2=$v2 v3=$v3"
}
## STDOUT:
v1=a,b,c
v1=d v2=e,f
v1=g v2=h v3=i
## END
## N-I dash STDOUT:
v1=
v1= v2=
v1= v2= v3=
## END

#### read -d '' (null-separated records)
printf 'a,b,c\0d,e,f\0g,h,i' | {
  IFS=,
  read -d '' v1
  echo "v1=$v1"
  read -d '' v1 v2
  echo "v1=$v1 v2=$v2"
  read -d '' v1 v2 v3
  echo "v1=$v1 v2=$v2 v3=$v3"
}
## STDOUT:
v1=a,b,c
v1=d v2=e,f
v1=g v2=h v3=i
## END
## N-I dash STDOUT:
v1=
v1= v2=
v1= v2= v3=
## END

#### read -rd
read -rd '' var <<EOF
foo
bar
EOF
echo "$var"
## STDOUT:
foo
bar
## END
## N-I dash stdout-json: "\n"

#### read -d when there's no delimiter
{ read -d : part
  echo $part $?
  read -d : part
  echo $part $?
} <<EOF
foo:bar
EOF
## STDOUT:
foo 0
bar 1
## END
## N-I dash STDOUT:
2
2
## END

#### read -t 0 tests if input is available
case $SH in (dash|zsh|mksh) exit ;; esac

# is there input available?
read -t 0 < /dev/null
echo $?

# floating point
read -t 0.0 < /dev/null
echo $?

# floating point
echo foo | { read -t 0; echo reply=$REPLY; }
echo $?

## STDOUT:
0
0
reply=
0
## END
## N-I dash/zsh/mksh stdout-json: ""

#### read -t 0.5
case $SH in (dash) exit ;; esac

read -t 0.5 < /dev/null
echo $?

## STDOUT:
1
## END
## BUG zsh/mksh STDOUT:
1
## END
## N-I dash stdout-json: ""

#### read -t -0.5 is invalid
# bash appears to just take the absolute value?

read -t -0.5 < /dev/null
echo $?

## STDOUT:
2
## END
## BUG bash STDOUT:
1
## END
## BUG zsh stdout-json: ""
## BUG zsh status: 1

#### read -u
case $SH in (dash|mksh) exit ;; esac

# file descriptor
read -u 3 3<<EOF
hi
EOF
echo reply=$REPLY
## STDOUT:
reply=hi
## END
## N-I dash/mksh stdout-json: ""

#### read -u syntax error
read -u -3
echo status=$?
## STDOUT:
status=2
## END
## OK bash/zsh STDOUT:
status=1
## END

#### read -N doesn't respect delimiter, while read -n does
case $SH in (dash|zsh|ash) exit ;; esac

echo foobar | { read -n 5 -d b; echo $REPLY; }
echo foobar | { read -N 5 -d b; echo $REPLY; }
## STDOUT:
foo
fooba
## END
## OK mksh STDOUT:
fooba
fooba
## END
## N-I dash/zsh/ash stdout-json: ""

#### read -p (not fully tested)

# hm DISABLED if we're not going to the terminal
# so we're only testing that it accepts the flag here

case $SH in (dash|mksh|zsh) exit ;; esac

echo hi | { read -p 'P'; echo $REPLY; }
echo hi | { read -p 'P' -n 1; echo $REPLY; }
## STDOUT:
hi
h
## END
## stderr-json: ""
## N-I dash/mksh/zsh stdout-json: ""

#### read usage
read -n -1
echo status=$?
## STDOUT:
status=2
## END
## OK bash stdout: status=1
## BUG mksh stdout-json: ""
# zsh gives a fatal error?  seems inconsistent
## BUG zsh stdout-json: ""
## BUG zsh status: 1

#### read with smooshed args
echo hi | { read -rn1 var; echo var=$var; }
## STDOUT:
var=h
## END
## N-I dash/zsh STDOUT:
var=
## END

#### read -r -d '' for NUL strings, e.g. find -print0


case $SH in (dash|zsh|mksh) exit ;; esac  # NOT IMPLEMENTED

mkdir -p read0
cd read0
rm -f *

touch a\\b\\c\\d  # -r is necessary!

find . -type f -a -print0 | { read -r -d ''; echo "[$REPLY]"; }

## STDOUT:
[./a\b\c\d]
## END
## N-I dash/zsh/mksh STDOUT:
## END


#### redirection from directory is non-fatal error)

# This tickles an infinite loop bug in our version of mksh!  TODO: upgrade the
# version and enable this
case $SH in (mksh) return ;; esac

cd $TMP
mkdir -p dir
read x < ./dir
echo status=$?

## STDOUT:
status=1
## END
# OK mksh stdout: status=2
## OK mksh stdout-json: ""

#### read -n from directory

case $SH in (dash|ash) return ;; esac  # not implemented

# same hanging bug
case $SH in (mksh) return ;; esac

mkdir -p dir
read -n 3 x < ./dir
echo status=$?
## STDOUT:
status=1
## END
## OK mksh stdout-json: ""
## N-I dash/ash stdout-json: ""

#### mapfile from directory (bash doesn't handle errors)
case $SH in (dash|ash|mksh|zsh) return ;; esac  # not implemented

mkdir -p dir
mapfile $x < ./dir
echo status=$?

## STDOUT:
status=1
## END
## BUG bash STDOUT:
status=0
## END
## N-I dash/ash/mksh/zsh stdout-json: ""

#### Redirect to directory
mkdir -p dir

echo foo > ./dir
echo status=$?
printf foo > ./dir
echo status=$?

## STDOUT:
status=1
status=1
## END
## OK dash STDOUT:
status=2
status=2
## END


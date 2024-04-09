## oils_failures_allowed: 0
## compare_shells: dash bash mksh zsh ash

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
echo

# backslash at end of line
echo -e '\
line2'
## STDOUT:
\
\
\
\

\
line2
## N-I dash STDOUT:
-e \
-e \
-e \
-e \

-e \
line2
## END

#### echo builtin should disallow typed args - literal
echo (42)
## status: 2
## OK mksh/zsh status: 1
## STDOUT:
## END

#### echo builtin should disallow typed args - variable
var x = 43
echo (x)
## status: 2
## OK mksh/zsh status: 1
## STDOUT:
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


#### echo to redirected directory is an error
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


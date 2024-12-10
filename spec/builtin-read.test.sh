## oils_failures_allowed: 2
## compare_shells: bash mksh zsh ash

#### read line from here doc

# NOTE: there are TABS below
read x <<EOF
A		B C D E
FG
EOF
echo "[$x]"
## stdout: [A		B C D E]
## status: 0

#### read from empty file
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

#### read builtin with no newline returns status 1

# This is odd because the variable is populated successfully.  OSH/YSH might
# need a separate put reading feature that doesn't use IFS.

echo -n ZZZ | { read x; echo status=$?; echo $x; }

## STDOUT:
status=1
ZZZ
## END
## status: 0

#### read builtin splits value across multiple vars
# NOTE: there are TABS below
read x y z <<EOF
A		B C D E 
FG
EOF
echo "[$x/$y/$z]"
## stdout: [A/B/C D E]
## status: 0

#### read builtin with too few variables
set -o errexit
set -o nounset  # hm this doesn't change it
read x y z <<EOF
A B
EOF
echo /$x/$y/$z/
## stdout: /A/B//
## status: 0

#### read -n (with $REPLY)
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

#### read -n doesn't strip whitespace (bug fix)
case $SH in dash|zsh) exit ;; esac

echo '  a b  ' | (read -n 4; echo "[$REPLY]")
echo '  a b  ' | (read -n 5; echo "[$REPLY]")
echo '  a b  ' | (read -n 6; echo "[$REPLY]")
echo

echo 'one var strips whitespace'
echo '  a b  ' | (read -n 4 myvar; echo "[$myvar]")
echo '  a b  ' | (read -n 5 myvar; echo "[$myvar]")
echo '  a b  ' | (read -n 6 myvar; echo "[$myvar]")
echo

echo 'three vars'
echo '  a b  ' | (read -n 4 x y z; echo "[$x] [$y] [$z]")
echo '  a b  ' | (read -n 5 x y z; echo "[$x] [$y] [$z]")
echo '  a b  ' | (read -n 6 x y z; echo "[$x] [$y] [$z]")

## STDOUT:
[  a ]
[  a b]
[  a b ]

one var strips whitespace
[a]
[a b]
[a b]

three vars
[a] [] []
[a] [b] []
[a] [b] []
## END

## N-I dash/zsh STDOUT:
## END

## BUG mksh STDOUT:
[a]
[a b]
[a b]

one var strips whitespace
[a]
[a b]
[a b]

three vars
[a] [] []
[a] [b] []
[a] [b] []
## END

#### read -d -n - respects delimiter and splits

case $SH in dash|zsh|ash) exit ;; esac

echo 'delim c'
echo '  a b c ' | (read -d 'c' -n 3; echo "[$REPLY]")
echo '  a b c ' | (read -d 'c' -n 4; echo "[$REPLY]")
echo '  a b c ' | (read -d 'c' -n 5; echo "[$REPLY]")
echo

echo 'one var'
echo '  a b c ' | (read -d 'c' -n 3 myvar; echo "[$myvar]")
echo '  a b c ' | (read -d 'c' -n 4 myvar; echo "[$myvar]")
echo '  a b c ' | (read -d 'c' -n 5 myvar; echo "[$myvar]")
echo

echo 'three vars'
echo '  a b c ' | (read -d 'c' -n 3 x y z; echo "[$x] [$y] [$z]")
echo '  a b c ' | (read -d 'c' -n 4 x y z; echo "[$x] [$y] [$z]")
echo '  a b c ' | (read -d 'c' -n 5 x y z; echo "[$x] [$y] [$z]")

## STDOUT:
delim c
[  a]
[  a ]
[  a b]

one var
[a]
[a]
[a b]

three vars
[a] [] []
[a] [] []
[a] [b] []
## END

## N-I dash/zsh/ash STDOUT:
## END

## BUG mksh STDOUT:
delim c
[a]
[a]
[a b]

one var
[a]
[a]
[a b]

three vars
[a] [] []
[a] [] []
[a] [b] []
## END


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
## N-I dash/ash stdout-json: ""

# zsh appears to hang with -k
## N-I zsh stdout-json: ""

#### read without args uses $REPLY, no splitting occurs (without -n)

# mksh and zsh implement splitting with $REPLY, bash/ash don't

echo '  a b  ' | (read; echo "[$REPLY]")
echo '  a b  ' | (read myvar; echo "[$myvar]")

echo '  a b  \
  line2' | (read; echo "[$REPLY]")
echo '  a b  \
  line2' | (read myvar; echo "[$myvar]")

# Now test with -r
echo '  a b  \
  line2' | (read -r; echo "[$REPLY]")
echo '  a b  \
  line2' | (read -r myvar; echo "[$myvar]")

## STDOUT:
[  a b  ]
[a b]
[  a b    line2]
[a b    line2]
[  a b  \]
[a b  \]
## END
## BUG mksh/zsh STDOUT:
[a b]
[a b]
[a b    line2]
[a b    line2]
[a b  \]
[a b  \]
## END
## BUG dash STDOUT:
[]
[a b  ]
[]
[a b    line2]
[]
[a b  \]
## END

#### read -n vs. -N
# dash, ash and zsh do not implement read -N
# mksh treats -N exactly the same as -n
case $SH in (dash|ash|zsh) exit ;; esac

# bash docs: https://www.gnu.org/software/bash/manual/html_node/Bash-Builtins.html

echo 'a b c' > $TMP/readn.txt

echo 'read -n'
read -n 5 A B C < $TMP/readn.txt; echo "'$A' '$B' '$C'"
read -n 4 A B C < $TMP/readn.txt; echo "'$A' '$B' '$C'"
echo

echo 'read -N'
read -N 5 A B C < $TMP/readn.txt; echo "'$A' '$B' '$C'"
read -N 4 A B C < $TMP/readn.txt; echo "'$A' '$B' '$C'"
## STDOUT:
read -n
'a' 'b' 'c'
'a' 'b' ''

read -N
'a b c' '' ''
'a b ' '' ''
## END
## N-I dash/ash/zsh stdout-json: ""
## BUG mksh STDOUT:
read -n
'a' 'b' 'c'
'a' 'b' ''

read -N
'a' 'b' 'c'
'a' 'b' ''
## END

#### read -N ignores delimiters
case $SH in (dash|ash|zsh) exit ;; esac

echo $'a\nb\nc' > $TMP/read-lines.txt

read -N 3 out < $TMP/read-lines.txt
echo "$out"
## STDOUT:
a
b
## END
## N-I dash/ash/zsh stdout-json: ""

#### read will unset extranous vars

echo 'a b' > $TMP/read-few.txt

c='some value'
read a b c < $TMP/read-few.txt
echo "'$a' '$b' '$c'"

case $SH in (dash) exit ;; esac # dash does not implement -n

c='some value'
read -n 3 a b c < $TMP/read-few.txt
echo "'$a' '$b' '$c'"
## STDOUT:
'a' 'b' ''
'a' 'b' ''
## END
## N-I dash STDOUT:
'a' 'b' ''
## END
## BUG zsh STDOUT:
'a' 'b' ''
'b' '' ''
## END

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

#### read with IFS=$'\n'
# The leading spaces are stripped if they appear in IFS.
IFS=$(echo -e '\n')
read var <<EOF
  a b c
  d e f
EOF
echo "[$var]"
## stdout: [  a b c]
## N-I dash stdout: [a b c]

#### read multiple lines with IFS=:
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

#### read with IFS=''
IFS=''
read x y <<EOF
  a b c d
EOF
echo "[$x|$y]"
## stdout: [  a b c d|]

#### read does not respect C backslash escapes

# bash doesn't respect these, but other shells do.  Gah!  I think bash
# behavior makes more sense.  It only escapes IFS.
echo '\a \b \c \d \e \f \g \h \x65 \145 \i' > $TMP/read-c.txt
read line < $TMP/read-c.txt
echo $line
## stdout-json: "a b c d e f g h x65 145 i\n"
## BUG ash stdout-json: "abcdefghx65 145 i\n"
## BUG dash/zsh stdout-json: "\u0007 \u0008\n"
## BUG mksh stdout-json: "\u0007 \u0008 d \u001b \u000c g h e 145 i\n"

#### dynamic scope used to set vars
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


#### read from redirected directory is non-fatal error

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

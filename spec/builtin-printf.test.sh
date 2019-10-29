#!/usr/bin/env bash
#
# printf
# bash-completion uses this odd printf -v construction.  It seems to mostly use
# %s and %q though.
#
# %s should just be
# declare $var='val'
#
# NOTE: 
# /usr/bin/printf %q "'" seems wrong.
# $ /usr/bin/printf  %q "'"
# ''\'''
#
# I suppose it is technically correct, but it looks very ugly.

#### printf with no args
printf
## status: 2
## OK dash/mksh/zsh status: 1
## stdout-json: ""

#### printf -v %s
var=foo
printf -v $var %s 'hello there'
argv.py "$foo"
## STDOUT:
['hello there']
## END
## N-I mksh/zsh/ash STDOUT:
-v['']
## END
## N-I dash STDOUT:
['']
## END

#### printf -v %q
val='"quoted" with spaces and \'

# quote 'val' and store it in foo
printf -v foo %q "$val"
# then round trip back to eval
eval "bar=$foo"

# debugging:
#echo foo="$foo"
#echo bar="$bar"
#echo val="$val"

test "$bar" = "$val" && echo OK
## STDOUT:
OK
## END
## N-I mksh/zsh/ash stdout-json: "-v"
## N-I mksh/zsh/ash status: 1
## N-I dash stdout-json: ""
## N-I dash status: 1

#### printf -v a[1]
a=(a b c)
printf -v 'a[1]' %s 'foo'
echo status=$?
argv.py "${a[@]}"
## STDOUT:
status=0
['a', 'foo', 'c']
## END
## N-I mksh/zsh STDOUT:
-vstatus=0
['a', 'b', 'c']
## END
## N-I dash/ash stdout-json: ""
## N-I dash/ash status: 2
## N-I osh STDOUT:
status=2
['a', 'b', 'c']
## END

#### dynamic declare instead of %s
var=foo
declare $var='hello there'
argv.py "$foo"
## STDOUT:
['hello there']
## END
## N-I dash/mksh/ash STDOUT:
['']
## END

#### dynamic declare instead of %q
var=foo
val='"quoted" with spaces and \'
# I think this is bash 4.4 only.
declare $var="${val@Q}"
echo "$foo"
## STDOUT:
'"quoted" with spaces and \'
## END
## N-I dash/ash stdout-json: ""
## N-I dash/ash status: 2
## N-I mksh stdout-json: "\n"
## N-I zsh stdout-json: ""
## N-I zsh status: 1

#### printf -v dynamic scope
case $SH in *mksh|*zsh|*dash|*/ash) echo not implemented; exit ;; esac
# OK so printf is like assigning to a var.
# printf -v foo %q "$bar" is like
# foo=${bar@Q}
dollar='dollar'
f() {
  local mylocal=foo
  printf -v dollar %q '$'  # assign foo to a quoted dollar
  printf -v mylocal %q 'mylocal'
  echo dollar=$dollar
  echo mylocal=$mylocal
}
echo dollar=$dollar
echo --
f
echo --
echo dollar=$dollar
echo mylocal=$mylocal
## STDOUT:
dollar=dollar
--
dollar=\$
mylocal=mylocal
--
dollar=\$
mylocal=
## END
## OK osh STDOUT:
dollar=dollar
--
dollar='$'
mylocal='mylocal'
--
dollar='$'
mylocal=
## END
## N-I dash/ash/mksh/zsh STDOUT:
not implemented
## END

#### printf with too few arguments
printf -- '-%s-%s-%s-\n' 'a b' 'x y'
## STDOUT:
-a b-x y--
## END

#### printf with too many arguments
printf -- '-%s-%s-\n' a b c d e
## STDOUT:
-a-b-
-c-d-
-e--
## END

#### printf width strings
printf '[%5s]\n' abc
printf '[%-5s]\n' abc
## STDOUT:
[  abc]
[abc  ]
## END

#### printf integer
printf '%d\n' 42
printf '%i\n' 42  # synonym
printf '%d\n' \'a # if first character is a quote, use character code
printf '%d\n' \"a # double quotes work too
printf '[%5d]\n' 42
printf '[%-5d]\n' 42
printf '[%05d]\n' 42
#printf '[%-05d]\n' 42  # the leading 0 is meaningless
#[42   ]
## STDOUT:
42
42
97
97
[   42]
[42   ]
[00042]
## END

#### printf %6.4d -- precision means something different for integers !?
printf '[%6.4d]\n' 42
## STDOUT:
[  0042]
## END
## N-I osh stdout-json: ""
## N-I osh status: 2

#### printf %6.4s does both truncation and padding
printf '[%6s]\n' foo
printf '[%6.4s]\n' foo
printf '[%-6.4s]\n' foo
printf '[%6s]\n' spam-eggs
printf '[%6.4s]\n' spam-eggs
printf '[%-6.4s]\n' spam-eggs
## STDOUT:
[   foo]
[   foo]
[foo   ]
[spam-eggs]
[  spam]
[spam  ]
## END

#### printf %6.0s and %0.0s
printf '[%6.0s]\n' foo
printf '[%0.0s]\n' foo
## STDOUT:
[      ]
[]
## END
## N-I mksh stdout-json: "[      ]\n["
## N-I mksh status: 1

#### unsigned / octal / hex
printf '[%u]\n' 42
printf '[%o]\n' 42
printf '[%x]\n' 42
printf '[%X]\n' 42
printf '[%X]\n' \'a  # if first character is a quote, use character code
printf '[%X]\n' \'ab  # extra chars ignored
## STDOUT:
[42]
[52]
[2a]
[2A]
[61]
[61]
## END

#### empty string (osh is more strict)
printf '%d\n' ''
## OK osh stdout-json: ""
## OK osh status: 1
## OK ash status: 1
## STDOUT:
0
## END

#### No char after ' (osh is more strict)

# most shells use 0 here
printf '%d\n' \' 

## OK osh stdout-json: ""
## OK osh status: 1
## OK mksh status: 1
## STDOUT:
0
## END

#### Unicode char with ' (osh is more strict)

# the mu character is U+03BC

printf '%x\n' \'μ

## STDOUT:
3bc
## END
## BUG dash/mksh/ash STDOUT:
ce
## END

#### negative numbers with unsigned / octal / hex
printf '[%u]\n' -42
printf '[%o]\n' -42
printf '[%x]\n' -42
printf '[%X]\n' -42
## STDOUT:
[18446744073709551574]
[1777777777777777777726]
[ffffffffffffffd6]
[FFFFFFFFFFFFFFD6]
## END

# osh DISALLOWS this because the output depends on the machine architecture.
## N-I osh stdout-json: ""
## N-I osh status: 1

#### printf floating point (not required, but they all implement it)
printf '[%f]\n' 3.14159
printf '[%.2f]\n' 3.14159
printf '[%8.2f]\n' 3.14159
printf '[%-8.2f]\n' 3.14159
printf '[%-f]\n' 3.14159
printf '[%-f]\n' 3.14
## STDOUT:
[3.141590]
[3.14]
[    3.14]
[3.14    ]
[3.141590]
[3.140000]
## END
## N-I osh stdout-json: ""
## N-I osh status: 2

#### printf floating point with - and 0
printf '[%8.4f]\n' 3.14
printf '[%08.4f]\n' 3.14
printf '[%8.04f]\n' 3.14  # meaning less 0
printf '[%08.04f]\n' 3.14
echo ---
# these all boil down to the same thing.  The -, 8, and 4 are respected, but
# none of the 0 are.
printf '[%-8.4f]\n' 3.14
printf '[%-08.4f]\n' 3.14
printf '[%-8.04f]\n' 3.14
printf '[%-08.04f]\n' 3.14
## STDOUT:
[  3.1400]
[003.1400]
[  3.1400]
[003.1400]
---
[3.1400  ]
[3.1400  ]
[3.1400  ]
[3.1400  ]
## END
## N-I osh STDOUT:
---
## END
## N-I osh status: 2

#### printf eE fF gG
printf '[%e]\n' 3.14
printf '[%E]\n' 3.14
printf '[%f]\n' 3.14
# bash is the only one that implements %F?  Is it a synonym?
#printf '[%F]\n' 3.14
printf '[%g]\n' 3.14
printf '[%G]\n' 3.14
## STDOUT:
[3.140000e+00]
[3.140000E+00]
[3.140000]
[3.14]
[3.14]
## END
## N-I osh stdout-json: ""
## N-I osh status: 2

#### printf backslash escapes
argv.py "$(printf 'a\tb')"
argv.py "$(printf '\xE2\x98\xA0')"
argv.py "$(printf '\044e')"
argv.py "$(printf '\0377')"  # out of range
## STDOUT:
['a\tb']
['\xe2\x98\xa0']
['$e']
['\x1f7']
## END
## N-I dash STDOUT:
['a\tb']
['\\xE2\\x98\\xA0']
['$e']
['\x1f7']
## END

#### printf octal backslash escapes
argv.py "$(printf '\0377')"
argv.py "$(printf '\377')"
## STDOUT:
['\x1f7']
['\xff']
## END

#### printf unicode backslash escapes
argv.py "$(printf '\u2620')"
argv.py "$(printf '\U0000065f')"
## STDOUT:
['\xe2\x98\xa0']
['\xd9\x9f']
## END
## N-I dash/ash STDOUT:
['\\u2620']
['\\U0000065f']
## END

#### printf invalid backslash escape (is ignored)
printf '[\Z]\n'
## STDOUT:
[\Z]
## END

#### printf % escapes
printf '[%%]\n'
## STDOUT:
[%]
## END

#### printf %b backslash escaping
printf '[%s]\n' '\044'  # escapes not evaluated
printf '[%b]\n' '\044'  # YES, escapes evaluated
echo status=$?
## STDOUT:
[\044]
[$]
status=0
## END
## N-I osh STDOUT:
[\044]
status=2
## END

#### printf %c -- doesn't respect UTF-8!  Bad.
twomu=$'\u03bc\u03bc'
printf '[%s]\n' "$twomu"
printf '%c' "$twomu" | wc --bytes
## STDOUT:
[μμ]
1
## END
## N-I dash STDOUT:
[$\u03bc\u03bc]
1
## END
## N-I ash STDOUT:
[\u03bc\u03bc]
1
## END
## N-I osh STDOUT:
[μμ]
0
## END

#### printf invalid format
printf '%z' 42
echo status=$?
printf '%-z' 42
echo status=$?
## STDOUT:
status=1
status=1
## END
# osh emits parse errors
## OK osh STDOUT:
status=2
status=2
## END
## BUG ash STDOUT:
status=0
status=0
## END

#### printf %q
x='a b'
printf '[%q]\n' "$x"
## STDOUT:
['a b']
## END
## OK bash/zsh STDOUT:
[a\ b]
## END
## N-I ash/dash stdout-json: "["
## N-I ash/dash status: 1

#### printf %6q (width)
# NOTE: coreutils /usr/bin/printf does NOT implement this %6q !!!
x='a b'
printf '[%6q]\n' "$x"
## STDOUT:
[ 'a b']
## END
## OK bash/zsh STDOUT:
[  a\ b]
## END
## N-I mksh/ash/dash stdout-json: "["
## N-I mksh/ash/dash status: 1

#### printf + and space flags
# I didn't know these existed -- I only knew about - and 0 !
printf '[%+d]\n' 42
printf '[%+d]\n' -42
printf '[% d]\n' 42
printf '[% d]\n' -42
## STDOUT:
[+42]
[-42]
[ 42]
[-42]
## END
## N-I osh stdout-json: ""
## N-I osh status: 2

#### printf # flag
# I didn't know these existed -- I only knew about - and 0 !
printf '[%#o]\n' 42
printf '[%#x]\n' 42
printf '[%#X]\n' 42
echo ---
printf '[%#f]\n' 3
## STDOUT:
[052]
[0x2a]
[0X2A]
---
[3.000000]
## END
## N-I osh STDOUT:
---
## END
## N-I osh status: 2

#### Runtime error for invalid integer
x=3abc
printf '%d\n' $x
echo status=$?
printf '%d\n' xyz
echo status=$?
## STDOUT:
3
status=1
0
status=1
## END
# zsh should exit 1 in both cases
## BUG zsh STDOUT:
0
status=1
0
status=0
## END
# fails but also prints 0 instead of 3abc
## BUG ash STDOUT:
0
status=1
0
status=1
## END
# osh doesn't print anything invalid
## OK osh STDOUT:
status=1
status=1
## END

#### %(strftime format)T
printf '%(%Y-%m-%d)T\n' 1557978599
echo status=$?
## STDOUT:
2019-05-15
status=0
## END
## N-I dash/mksh/zsh/ash STDOUT:
status=1
## END
## N-I osh STDOUT:
status=2
## END

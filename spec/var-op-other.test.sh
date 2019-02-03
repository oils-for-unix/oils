#!/usr/bin/env bash
#
# Test combination of var ops.
#
# NOTE: There are also slice tests in {array,arith-context}.test.sh.

#### Cannot take length of substring slice
# These are runtime errors, but we could make them parse time errors.
v=abcde
echo ${#v:1:3}
## status: 1
## OK osh status: 2
# zsh actually implements this!
## OK zsh stdout: 3
## OK zsh status: 0

#### Pattern replacement
v=abcde
echo ${v/c*/XX}
## stdout: abXX

#### Pattern replacement on unset variable
echo -${v/x/y}-
echo status=$?
set -o nounset  # make sure this fails
echo -${v/x/y}-
## STDOUT:
--
status=0
## BUG mksh STDOUT:
# patsub disrespects nounset!
--
status=0
--
## status: 1
## BUG mksh status: 0

#### Global Pattern replacement with /
s=xx_xx_xx
echo ${s/xx?/yy_} ${s//xx?/yy_}
## stdout: yy_xx_xx yy_yy_xx

#### Left Anchored Pattern replacement with #
s=xx_xx_xx
echo ${s/?xx/_yy} ${s/#?xx/_yy}
## stdout: xx_yy_xx xx_xx_xx

#### Right Anchored Pattern replacement with %
s=xx_xx_xx
echo ${s/?xx/_yy} ${s/%?xx/_yy}
## stdout: xx_yy_xx xx_xx_yy

#### Replace fixed strings
s=xx_xx
echo ${s/xx/yy} ${s//xx/yy} ${s/#xx/yy} ${s/%xx/yy}
## stdout: yy_xx yy_yy yy_xx xx_yy

#### Replace is longest match
# If it were shortest, then you would just replace the first <html>
s='begin <html></html> end'
echo ${s/<*>/[]}
## stdout: begin [] end

#### Replace char class
s=xx_xx_xx
echo ${s//[[:alpha:]]/y} ${s//[^[:alpha:]]/-}
## stdout: yy_yy_yy xx-xx-xx
## N-I mksh stdout: xx_xx_xx xx_xx_xx

#### Replace hard glob
s='aa*bb+cc'
echo ${s//\**+/__}  # Literal *, then any sequence of characters, then literal +
## stdout: aa__cc

#### Pattern replacement ${v/} is not valid
v=abcde
echo -${v/}-
echo status=$?
## status: 2
## stdout-json: ""
## BUG bash/mksh/zsh status: 0
## BUG bash/mksh/zsh stdout-json: "-abcde-\nstatus=0\n"

#### Pattern replacement ${v//} is not valid
v='a/b/c'
echo -${v//}-
echo status=$?
## status: 2
## stdout-json: ""
## BUG bash/mksh/zsh status: 0
## BUG bash/mksh/zsh stdout-json: "-a/b/c-\nstatus=0\n"

#### ${v/a} is the same as ${v/a/}  -- no replacement string
v='aabb'
echo ${v/a}
echo status=$?
## STDOUT:
abb
status=0
## END

#### Replacement with special chars (bug fix)
v=xx
echo ${v/x/"?"}
## stdout: ?x

#### String slice
foo=abcdefg
echo ${foo:1:3}
## STDOUT:
bcd
## END

#### Out of range string slice: begin
# out of range begin doesn't raise error in bash, but in mksh it skips the
# whole thing!
foo=abcdefg
echo _${foo:100:3}
echo $?
## STDOUT:
_
0
## END
## BUG mksh stdout-json: "\n0\n"

#### Out of range string slice: length
# OK in both bash and mksh
foo=abcdefg
echo _${foo:3:100}
echo $?
## STDOUT:
_defg
0
## END
## BUG mksh stdout-json: "_defg\n0\n"

#### String slice: negative begin
foo=abcdefg
echo ${foo: -4:3}
## OK osh stdout:
## stdout: def

#### String slice: negative second arg is position, not length
foo=abcdefg
echo ${foo:3:-1} ${foo: 3: -2} ${foo:3 :-3 }
## OK osh stdout:
## stdout: def de d
## BUG mksh stdout: defg defg defg

#### strict-word-eval with string slice
set -o strict-word-eval || true
echo slice
s='abc'
echo -${s: -2}-
## stdout-json: "slice\n"
## status: 1
## N-I bash status: 0
## N-I bash stdout-json: "slice\n-bc-\n"
## N-I mksh/zsh status: 1
## N-I mksh/zsh stdout-json: ""

#### String slice with math
# I think this is the $(()) language inside?
i=1
foo=abcdefg
echo ${foo: i+4-2 : i + 2}
## stdout: def

#### Slice undefined
echo -${undef:1:2}-
set -o nounset
echo -${undef:1:2}-
echo -done-
## STDOUT:
--
## END
## status: 1
# mksh doesn't respect nounset!
## BUG mksh status: 0
## BUG mksh STDOUT:
--
--
-done-
## END

#### Slice UTF-8 String
# mksh slices by bytes.
foo='--μ--'
echo ${foo:1:3}
## stdout: -μ-
## BUG mksh stdout: -μ

#### Slice string with invalid UTF-8 results in empty string and warning
s=$(echo -e "\xFF")bcdef
echo -${s:1:3}-
## status: 0
## stdout-json: "--\n"
## stderr-json: "osh warning: Invalid start of UTF-8 character\n"
## BUG bash/mksh/zsh status: 0
## BUG bash/mksh/zsh stdout-json: "-bcd-\n"
## BUG bash/mksh/zsh stderr-json: ""


#### Slice string with invalid UTF-8 with strict-word-eval
set -o strict-word-eval || true
echo slice
s=$(echo -e "\xFF")bcdef
echo -${s:1:3}-
## status: 1
## stdout-json: "slice\n"
## N-I mksh/zsh status: 1
## N-I mksh/zsh stdout-json: ""
## N-I bash status: 0
## N-I bash stdout-json: "slice\n-bcd-\n"

#### Lower Case with , and ,,
x='ABC DEF'
echo ${x,}
echo ${x,,}
## STDOUT:
aBC DEF
abc def
## END
## N-I mksh/zsh stdout-json: ""
## N-I mksh/zsh status: 1


#### Upper Case with ^ and ^^
x='abc def'
echo ${x^}
echo ${x^^}
## STDOUT:
Abc def
ABC DEF
## END
## N-I mksh/zsh stdout-json: ""
## N-I mksh/zsh status: 1

#### Lower Case with constant string (VERY WEIRD)
x='AAA ABC DEF'
echo ${x,A}
echo ${x,,A}  # replaces every A only?
## STDOUT:
aAA ABC DEF
aaa aBC DEF
## END
## N-I mksh/zsh stdout-json: ""
## N-I mksh/zsh status: 1

#### Lower Case glob
x='ABC DEF'
echo ${x,[d-f]}
echo ${x,,[d-f]}  # This seems buggy, it doesn't include F?
## STDOUT:
ABC DEF
ABC deF
## END
## N-I mksh/zsh stdout-json: ""
## N-I mksh/zsh status: 1

#### ${x@Q}
x="FOO'BAR spam\"eggs"
eval "new=${x@Q}"
test "$x" = "$new" && echo OK
## STDOUT:
OK
## END
## N-I zsh stdout-json: ""
## N-I zsh status: 1


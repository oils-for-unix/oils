#!/usr/bin/env bash
#
# Test combination of var ops.
#
# NOTE: There are also slice tests in {array,arith-context}.test.sh.

#### String slice
foo=abcdefg
echo ${foo:1:3}
## STDOUT:
bcd
## END

#### Cannot take length of substring slice
# These are runtime errors, but we could make them parse time errors.
v=abcde
echo ${#v:1:3}
## status: 1
## OK osh status: 2
# zsh actually implements this!
## OK zsh stdout: 3
## OK zsh status: 0

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


#### strict_word_eval with string slice
shopt -s strict_word_eval || true
echo slice
s='abc'
echo -${s: -2}-
## STDOUT:
slice
## END
## status: 1
## N-I bash/mksh/zsh status: 0
## N-I bash/mksh/zsh STDOUT:
slice
-bc-
## END

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
## STDOUT:
--
## END
## STDERR:
[??? no location ???] warning: Invalid start of UTF-8 character
## END
## BUG bash/mksh/zsh status: 0
## BUG bash/mksh/zsh STDOUT:
-bcd-
## END
## BUG bash/mksh/zsh stderr-json: ""


#### Slice string with invalid UTF-8 with strict_word_eval
shopt -s strict_word_eval || true
echo slice
s=$(echo -e "\xFF")bcdef
echo -${s:1:3}-
## status: 1
## STDOUT: 
slice
## END
## N-I bash/mksh/zsh status: 0
## N-I bash/mksh/zsh STDOUT:
slice
-bcd-
## END

#### Slice with an index that's an array itself not allowed
i=(3 4 5)
mystr=abcdefg
echo assigned
echo ${mystr:$i:2}
## status: 1
## STDOUT:
assigned
## END
## BUG mksh/bash status: 0
## BUG mksh/bash STDOUT:
assigned
de
## END

#### Slice with an assoc array
declare -A A=(['5']=3 ['6']=4)
mystr=abcdefg
echo assigned
echo ${mystr:$A:2}
## status: 1
## STDOUT:
assigned
## END
## N-I mksh stdout-json: ""
## BUG bash/zsh status: 0
## BUG bash/zsh STDOUT:
assigned
ab
## END

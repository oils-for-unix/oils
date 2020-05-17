#!/usr/bin/env bash

#### Lazy Evaluation of Alternative
i=0
x=x
echo ${x:-$((i++))}
echo $i
echo ${undefined:-$((i++))}
echo $i  # i is one because the alternative was only evaluated once
## status: 0
## stdout-json: "x\n0\n0\n1\n"
## N-I dash status: 2
## N-I dash stdout-json: "x\n0\n"

#### Default value when empty
empty=''
echo ${empty:-is empty}
## stdout: is empty

#### Default value when unset
echo ${unset-is unset}
## stdout: is unset

#### Unquoted with array as default value
set -- '1 2' '3 4'
argv.py X${unset=x"$@"x}X
argv.py X${unset=x$@x}X  # If you want OSH to split, write this
# osh
## STDOUT:
['Xx1', '2', '3', '4xX']
['Xx1', '2', '3', '4xX']
## END
## OK osh STDOUT:
['Xx1 2', '3 4xX']
['Xx1', '2', '3', '4xX']
## END

#### Quoted with array as default value
set -- '1 2' '3 4'
argv.py "X${unset=x"$@"x}X"
argv.py "X${unset=x$@x}X"  # OSH is the same here
## STDOUT:
['Xx1 2 3 4xX']
['Xx1 2 3 4xX']
## END
## BUG bash STDOUT:
['Xx1', '2', '3', '4xX']
['Xx1 2 3 4xX']
## END
## OK osh STDOUT:
['Xx1 2', '3 4xX']
['Xx1 2 3 4xX']
## END

#### Assign default with array
set -- '1 2' '3 4'
argv.py X${unset=x"$@"x}X
argv.py "$unset"
## STDOUT:
['Xx1', '2', '3', '4xX']
['x1 2 3 4x']
## END
## OK osh STDOUT:
['Xx1 2', '3 4xX']
['x1 2 3 4x']
## END

#### Assign default value when empty
empty=''
${empty:=is empty}
echo $empty
## stdout: is empty

#### Assign default value when unset
${unset=is unset}
echo $unset
## stdout: is unset

#### ${v:+foo} Alternative value when empty
v=foo
empty=''
echo ${v:+v is not empty} ${empty:+is not empty}
## stdout: v is not empty

#### ${v+foo} Alternative value when unset
v=foo
echo ${v+v is not unset} ${unset:+is not unset}
## stdout: v is not unset

#### ${v+foo} and ${v:+foo} when set -u
set -u
v=v
echo v=${v:+foo}
echo v=${v+foo}
unset v
echo v=${v:+foo}
echo v=${v+foo}
## STDOUT:
v=foo
v=foo
v=
v=
## END

#### ${v-foo} and ${v:-foo} when set -u
set -u
v=v
echo v=${v:-foo}
echo v=${v-foo}
unset v
echo v=${v:-foo}
echo v=${v-foo}
## STDOUT:
v=v
v=v
v=foo
v=foo
## END

#### array and - and +
case $SH in (dash) exit ;; esac

shopt -s compat_array  # to refer to array as scalar

empty=()
a1=('')
a2=('' x)
a3=(3 4)
echo empty=${empty[@]-minus}
echo a1=${a1[@]-minus}
echo a1[0]=${a1[0]-minus}
echo a2=${a2[@]-minus}
echo a3=${a3[@]-minus}
echo ---

echo empty=${empty[@]+plus}
echo a1=${a1[@]+plus}
echo a1[0]=${a1[0]+plus}
echo a2=${a2[@]+plus}
echo a3=${a3[@]+plus}
echo ---

echo empty=${empty+plus}
echo a1=${a1+plus}
echo a2=${a2+plus}
echo a3=${a3+plus}

## STDOUT:
empty=minus
a1=
a1[0]=
a2= x
a3=3 4
---
empty=
a1=plus
a1[0]=plus
a2=plus
a3=plus
---
empty=
a1=plus
a2=plus
a3=plus
## END
## N-I dash stdout-json: ""

#### $@ and - and +
echo argv=${@-minus}
echo argv=${@+plus}
## STDOUT:
argv=minus
argv=
## END
## BUG dash STDOUT:
argv=
argv=plus
## END

#### Error when empty
empty=''
echo ${empty:?'is em'pty}  # test eval of error
echo should not get here
## stdout-json: ""
## status: 1
## OK dash status: 2

#### Error when unset
echo ${unset?is empty}
echo should not get here
## stdout-json: ""
## status: 1
## OK dash status: 2

#### Error when unset
v=foo
echo ${v+v is not unset} ${unset:+is not unset}
## stdout: v is not unset

#### ${var=x} dynamic scope
f() { : "${hello:=x}"; echo $hello; }
f
echo hello=$hello

f() { hello=x; }
f
echo hello=$hello
## STDOUT:
x
hello=x
hello=x
## END
 
#### array ${arr[0]=x}
arr=()
echo ${#arr[@]}
: ${arr[0]=x}
echo ${#arr[@]}
## STDOUT:
0
1
## END
## N-I dash status: 2
## N-I dash stdout-json: ""

#### assoc array ${arr["k"]=x}
# note: this also works in zsh

declare -A arr=()
echo ${#arr[@]}
: ${arr['k']=x}
echo ${#arr[@]}
## STDOUT:
0
1
## END
## N-I dash status: 2
## N-I dash stdout-json: ""
## N-I mksh status: 1
## N-I mksh stdout-json: ""

#### "\z" as arg
echo "${undef-\$}"
echo "${undef-\(}"
echo "${undef-\z}"
echo "${undef-\"}"
echo "${undef-\`}"
echo "${undef-\\}"
## STDOUT:
$
\(
\z
"
`
\
## END
## BUG yash STDOUT:
$
(
z
"
`
\
## END

#### "\e" as arg
echo "${undef-\e}"
## STDOUT:
\e
## END
## BUG zsh/mksh stdout-repr: '\x1b\n'
## BUG yash stdout: e


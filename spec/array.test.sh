#!/usr/bin/env bash

# TODO: Need a SETUP section.

#### SETUP
a=(1 '2 3')

#### "${a[@]}" and "${a[*]}"
a=(1 '2 3')
argv.py "${a[@]}" "${a[*]}"
## stdout: ['1', '2 3', '1 2 3']

#### ${a[@]} and ${a[*]}
a=(1 '2 3')
argv.py ${a[@]} ${a[*]}
## stdout: ['1', '2', '3', '1', '2', '3']

#### 4 ways to interpolate empty array
argv.py 1 "${a[@]}" 2 ${a[@]} 3 "${a[*]}" 4 ${a[*]} 5
## stdout: ['1', '2', '3', '', '4', '5']

#### empty array
empty=()
argv.py "${empty[@]}"
## stdout: []

#### Empty array with :-
empty=()
argv.py ${empty[@]:-not one} "${empty[@]:-not one}"
## stdout: ['not', 'one', 'not one']

#### nounset with empty array (design bug, makes it hard to use arrays)
# http://lists.gnu.org/archive/html/help-bash/2017-09/msg00005.html
# NOTE: This used to be a bug in bash 4.3, but is fixed in bash 4.4.
set -o nounset
empty=()
argv.py "${empty[@]}"
echo status=$?
## STDOUT:
[]
status=0
## END
## BUG mksh stdout-json: ""
## BUG mksh status: 1

#### local array
# mksh support local variables, but not local arrays, oddly.
f() {
  local a=(1 '2 3')
  argv.py "${a[0]}"
}
f
## stdout: ['1']
## status: 0
## BUG mksh status: 1
## BUG mksh stdout-json: ""

#### Command with with word splitting in array
array=('1 2' $(echo '3 4'))
argv.py "${array[@]}"
## stdout: ['1 2', '3', '4']

#### space before ( in array initialization
# NOTE: mksh accepts this, but bash doesn't
a= (1 '2 3')
echo $a
## status: 2
## OK mksh status: 0
## OK mksh stdout: 1

#### array over multiple lines
a=(
1
'2 3'
)
argv.py "${a[@]}"
## stdout: ['1', '2 3']
## status: 0

#### array with invalid token
a=(
1
&
'2 3'
)
argv.py "${a[@]}"
## status: 2
## OK mksh status: 1

#### array with empty string
empty=('')
argv.py "${empty[@]}"
## stdout: ['']

#### Retrieve index
a=(1 '2 3')
argv.py "${a[1]}"
## stdout: ['2 3']

#### Retrieve out of bounds index
a=(1 '2 3')
argv.py "${a[3]}"
## stdout: ['']

#### Negative index
a=(1 '2 3')
argv.py "${a[-1]}" "${a[-2]}" "${a[-5]}"  # last one out of bounds
## stdout: ['2 3', '1', '']
## N-I mksh stdout: ['', '', '']

#### Retrieve index that is a variable
a=(1 '2 3')
i=1
argv.py "${a[$i]}"
## stdout: ['2 3']

#### Retrieve index that is a variable without $
a=(1 '2 3')
i=5
argv.py "${a[i-4]}"
## stdout: ['2 3']

#### Retrieve index that is a command sub
a=(1 '2 3')
argv.py "${a[$(echo 1)]}"
## stdout: ['2 3']

#### Retrieve array indices with ${!a}
a=(1 '2 3')
argv.py "${!a[@]}"
## stdout: ['0', '1']

#### Retrieve sparse array indices with ${!a}
a=()
(( a[99]=1 ))
argv.py "${!a[@]}"
## STDOUT:
['99']
## END

#### ${!a[1]} is named ref in bash
# mksh ignores it
foo=bar
a=('1 2' foo '2 3')
argv.py "${!a[1]}"
## status: 0
## stdout: ['bar']
## N-I mksh stdout: ['a[1]']

#### ${!a} on array is disallowed
# bash gives empty string because it's like a[0]
# mksh gives the name of the variable with !.  Very weird.
a=(1 '2 3')
argv.py "${!a}"
## stdout-json: ""
## status: 1
## BUG bash stdout: ['']
## BUG bash status: 0
## BUG mksh stdout: ['a']
## BUG mksh status: 0

#### All elements unquoted
a=(1 '2 3')
argv.py ${a[@]}
## stdout: ['1', '2', '3']

#### All elements quoted
a=(1 '2 3')
argv.py "${a[@]}"
## stdout: ['1', '2 3']

#### $*
a=(1 '2 3')
argv.py ${a[*]}
## stdout: ['1', '2', '3']

#### "$*"
a=(1 '2 3')
argv.py "${a[*]}"
## stdout: ['1 2 3']

#### Interpolate array into array
a=(1 '2 3')
a=(0 "${a[@]}" '4 5')
argv.py "${a[@]}"
## stdout: ['0', '1', '2 3', '4 5']

#### Exporting array doesn't do anything, not even first element
# bash parses, but doesn't execute.
# mksh gives syntax error -- parses differently with 'export'
# osh no longer parses this statically.
export PYTHONPATH=(a b c)
export PYTHONPATH=a  # NOTE: in bash, this doesn't work afterward!
printenv.py PYTHONPATH
## stdout-json: ""
## status: 1
## OK bash stdout: None
## OK bash status: 0

#### Arrays can't be used as env bindings
# Hm bash it treats it as a string!
A=a B=(b b) printenv.py A B
## status: 2
## stdout-json: ""
## OK bash stdout-json: "a\n(b b)\n"
## OK bash status: 0
## OK mksh status: 1

#### Set element
a=(1 '2 3')
a[0]=9
argv.py "${a[@]}"
## stdout: ['9', '2 3']

#### Set element with var ref
a=(1 '2 3')
i=0
a[$i]=9
argv.py "${a[@]}"
## stdout: ['9', '2 3']

#### Set element with array ref
# This makes parsing a little more complex.  Anything can be inside [],
# including other [].
a=(1 '2 3')
i=(0 1)
a[${i[1]}]=9
argv.py "${a[@]}"
## stdout: ['1', '9']

#### Set array item to array
a=(1 2)
a[0]=(3 4)
echo "status=$?"
## stdout-json: ""
## status: 2
## N-I mksh status: 1
## BUG bash stdout: status=1
## BUG bash status: 0

#### Slice of array with [@]
# mksh doesn't support this syntax!  It's a bash extension.
a=(1 2 3)
argv.py "${a[@]:1:2}"
## stdout: ['2', '3']
## N-I mksh status: 1
## N-I mksh stdout-json: ""

#### Negative slice begin
# mksh doesn't support this syntax!  It's a bash extension.
# NOTE: for some reason -2) has to be in parens?  Ah that's because it
# conflicts with :-!  That's silly.  You can also add a space.
a=(1 2 3 4 5)
argv.py "${a[@]:(-4)}"
## stdout: ['2', '3', '4', '5']
## N-I mksh status: 1
## N-I mksh stdout-json: ""

#### Negative slice length
a=(1 2 3 4 5)
argv.py "${a[@]: 1: -3}"
## status: 1
## stdout-json: ""

#### Slice with arithmetic
a=(1 2 3)
i=5
argv.py "${a[@]:i-4:2}"
## stdout: ['2', '3']
## N-I mksh status: 1
## N-I mksh stdout-json: ""

#### Number of elements
a=(1 '2 3')
echo "${#a[@]}" ${#a[@]}  # bug fix: also test without quotes
## stdout: 2 2

#### Length of an element
a=(1 '2 3')
echo "${#a[1]}"
## stdout: 3

#### Iteration
a=(1 '2 3')
for v in "${a[@]}"; do
  echo $v
done
## stdout-json: "1\n2 3\n"

#### glob within array yields separate elements
touch _tmp/y.Y _tmp/yy.Y
a=(_tmp/*.Y)
argv.py "${a[@]}"
## stdout: ['_tmp/y.Y', '_tmp/yy.Y']

#### declare array and then append
declare -a array
array+=(a)
array+=(b c)
argv.py "${array[@]}"
## stdout: ['a', 'b', 'c']

#### Array syntax in wrong place
ls foo=(1 2)
## status: 1
## OK bash status: 2

#### Single array with :-
# bash does EMPTY ELISION here, unless it's double quoted.  mksh has
# more sane behavior.  OSH is better.
single=('')
argv.py ${single[@]:-none} x "${single[@]:-none}"
## OK osh stdout: ['x', '']
## OK bash stdout: ['none', 'x', '']
## OK mksh stdout: ['none', 'x', 'none']

#### Stripping a whole array unquoted
# Problem: it joins it first.
files=('foo.c' 'sp ace.h' 'bar.c')
argv.py ${files[@]%.c}
## status: 0
## stdout: ['foo', 'sp', 'ace.h', 'bar']
## N-I mksh status: 1
## N-I mksh stdout-json: ""

#### Stripping a whole array quoted
files=('foo.c' 'sp ace.h' 'bar.c')
argv.py "${files[@]%.c}"
## status: 0
## stdout: ['foo', 'sp ace.h', 'bar']
## N-I mksh status: 1
## N-I mksh stdout-json: ""

#### Multiple subscripts not allowed
# NOTE: bash 4.3 had a bug where it ignored the bad subscript, but now it is
# fixed.
a=('123' '456')
argv.py "${a[0]}" "${a[0][0]}"
## stdout-json: ""
## status: 2
## OK bash/mksh status: 1

#### Length op, index op, then transform op is not allowed
a=('123' '456')
echo "${#a[0]}" "${#a[0]/1/xxx}"
## stdout-json: ""
## status: 2
## OK bash/mksh status: 1

#### Array subscript not allowed on string
s='abc'
echo ${s[@]}
## BUG bash/mksh status: 0
## BUG bash/mksh stdout: abc
## status: 1

#### Create a "user" array out of the argv array
set -- 'a b' 'c'
array1=('x y' 'z')
array2=("$@")
argv.py "${array1[@]}" "${array2[@]}"
## stdout: ['x y', 'z', 'a b', 'c']

#### Tilde expansion within array
HOME=/home/bob
a=(~/src ~/git)
echo "${a[@]}"
## stdout: /home/bob/src /home/bob/git

#### Brace Expansion within Array
a=(-{a,b} {c,d}-)
echo "${a[@]}"
## stdout: -a -b c- d-

#### array default
default=('1 2' '3')
argv.py "${undef[@]:-${default[@]}}"
## stdout: ['1 2', '3']

#### Singleton Array Copy and Assign.  OSH can't index strings with ints
a=( '12 3' )
b=( "${a[@]}" )
c="${a[@]}"  # This decays it to a string
d=${a[*]}  # This decays it to a string
echo ${#a[0]} ${#b[0]}
echo ${#a[@]} ${#b[@]}

# osh is intentionally stricter, and these fail.
echo ${#c[0]} ${#d[0]}
echo ${#c[@]} ${#d[@]}

## status: 1
## STDOUT:
4 4
1 1
## END
## OK bash/mksh status: 0
## OK bash/mksh STDOUT:
4 4
1 1
4 4
1 1
## END

#### declare -a / local -a is empty array
declare -a myarray
argv.py "${myarray[@]}"
myarray+=('x')
argv.py "${myarray[@]}"

f() {
  local -a myarray
  argv.py "${myarray[@]}"
  myarray+=('x')
  argv.py "${myarray[@]}"
}
f
## STDOUT:
[]
['x']
[]
['x']
## END

#### Create sparse array
a=()
(( a[99]=1 )) # osh doesn't parse index assignment outside arithmetic yet
echo len=${#a[@]}
argv.py "${a[@]}"
echo "unset=${a[33]}"
echo len-of-unset=${#a[33]}
## STDOUT:
len=1
['1']
unset=
len-of-unset=0
## END

#### Create sparse array implicitly
(( a[99]=1 ))
echo len=${#a[@]}
argv.py "${a[@]}"
echo "unset=${a[33]}"
echo len-of-unset=${#a[33]}
## STDOUT:
len=1
['1']
unset=
len-of-unset=0
## END

#### Append sparse arrays
a=()
(( a[99]=1 ))
b=()
(( b[33]=2 ))
(( b[66]=3 ))
a+=( "${b[@]}" )
argv.py "${a[@]}"
argv.py "${a[99]}" "${a[100]}" "${a[101]}"
## STDOUT:
['1', '2', '3']
['1', '2', '3']
## END

#### Slice of sparse array with [@]
# mksh doesn't support this syntax!  It's a bash extension.
(( a[33]=1 ))
(( a[66]=2 ))
(( a[99]=2 ))
argv.py "${a[@]:15:2}"
## stdout: ['1', '2']
## N-I mksh status: 1
## N-I mksh stdout-json: ""

#### Using an array itself as the index on LHS
shopt -u strict_arith
a[a]=42
a[a]=99
argv.py "${a[@]}" "${a[0]}" "${a[42]}" "${a[99]}"

## status: 1
## stdout-json: ""

## BUG bash/mksh status: 0
## BUG bash/mksh STDOUT:
['42', '99', '42', '99', '']
## END

#### Using an array itself as the index on RHS
shopt -u strict_arith
a=(1 2 3)
(( x = a[a] ))
echo $x
## status: 1
## stdout-json: ""
## BUG bash/mksh status: 0
## BUG bash/mksh STDOUT:
2
## END

#### a[$x$y] on LHS and RHS
x=1
y=2
a[$x$y]=foo

# not allowed by OSH parsing
#echo ${a[$x$y]}

echo ${a[12]}
echo ${#a[@]}

## STDOUT:
foo
1
## END

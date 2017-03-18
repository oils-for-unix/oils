#!/bin/bash

# TODO: Need a SETUP section.

### SETUP
a=(1 '2 3')

### $a gives first element of array
a=(1 '2 3')
echo $a
# stdout: 1

### "${a[@]}" and "${a[*]}"
a=(1 '2 3')
argv.py "${a[@]}" "${a[*]}"
# stdout: ['1', '2 3', '1 2 3']

### ${a[@]} and ${a[*]}
a=(1 '2 3')
argv.py ${a[@]} ${a[*]}
# stdout: ['1', '2', '3', '1', '2', '3']

### local array
# mksh support local variables, but not local arrays, oddly.
f() {
  local a=(1 '2 3')
  argv.py "${a[0]}"
}
f
# stdout: ['1']
# status: 0
# BUG mksh status: 1
# BUG mksh stdout-json: ""

### Command with with word splitting in array
array=('1 2' $(echo '3 4'))
argv.py "${array[@]}"
# stdout: ['1 2', '3', '4']

### space before ( in array initialization
# NOTE: mksh accepts this, but bash doesn't
a= (1 '2 3')
echo $a
# status: 2
# OK mksh status: 0
# OK mksh stdout: 1

### empty array
empty=()
argv.py "${empty[@]}"
# stdout: []

### array with empty string
empty=('')
argv.py "${empty[@]}"
# stdout: ['']

### Assign to array index without initialization
b[2]=9
argv.py "${b[@]}"
# stdout: ['9']

### Retrieve index
a=(1 '2 3')
argv.py "${a[1]}"
# stdout: ['2 3']

### Retrieve out of bounds index
a=(1 '2 3')
argv.py "${a[3]}"
# stdout: ['']

### Retrieve index that is a variable
a=(1 '2 3')
i=1
argv.py "${a[$i]}"
# stdout: ['2 3']

### Retrieve index that is a variable without $
a=(1 '2 3')
i=5
argv.py "${a[i-4]}"
# stdout: ['2 3']

### Retrieve index that is a command sub
a=(1 '2 3')
argv.py "${a[$(echo 1)]}"
# stdout: ['2 3']

### Retrieve all indices with !
a=(1 '2 3')
argv.py "${!a[@]}"
# stdout: ['0', '1']

### Retrieve indices for one value
# Not really standardized between bash and mksh.  Just doing whatever bash
# does.
a=(4 '2 3')
argv.py "${!a[1]}"
# status: 0
# stdout: ['']
# OK mksh stdout: ['1']

### Retrieve indices without []
# bash gives empty string?
# mksh gives the name of the variable with !.  Very weird.
a=(1 '2 3')
argv.py "${!a}"
# stdout: ['']
# OK mksh stdout: ['a']

### All elements unquoted
a=(1 '2 3')
argv.py ${a[@]}
# stdout: ['1', '2', '3']

### All elements quoted
a=(1 '2 3')
argv.py "${a[@]}"
# stdout: ['1', '2 3']

### $*
a=(1 '2 3')
argv.py ${a[*]}
# stdout: ['1', '2', '3']

### "$*"
a=(1 '2 3')
argv.py "${a[*]}"
# stdout: ['1 2 3']

### Interpolate array into array
a=(1 '2 3')
a=(0 "${a[@]}" '4 5')
argv.py "${a[@]}"
# stdout: ['0', '1', '2 3', '4 5']

### Arrays can't be copied directly
declare -a a b
a=(x y z)
b="${a[@]}"  # this collapses to a string
c=("${a[@]}")  # this preserves the array
c[1]=YYY  # mutate a copy -- doesn't affect the original
argv.py "${a[@]}" "${b[@]}" "${c[@]}"
# stdout: ['x', 'y', 'z', 'x y z', 'x', 'YYY', 'z']

### Exporting array doesn't do anything, not even first element
# bash parses, but doesn't execute.
# mksh gives syntax error -- parses differently with 'export'
export PYTHONPATH=(a b c)
export PYTHONPATH=a  # NOTE: in bash, this doesn't work afterward!
printenv.py PYTHONPATH
# stdout: None
# BUG mksh stdout-json: ""
# BUG mksh status: 1

### Env with array
# Hm it treats it as a string!
A=a B=(b b) printenv.py A B
# stdout-json: "a\n(b b)\n"
# BUG mksh stdout-json: ""
# BUG mksh status: 1

### Set element
a=(1 '2 3')
a[0]=9
argv.py "${a[@]}"
# stdout: ['9', '2 3']

### Set element with var ref
a=(1 '2 3')
i=0
a[$i]=9
argv.py "${a[@]}"
# stdout: ['9', '2 3']

### Set element with array ref
# This makes parsing a little more complex.  Anything can be inside [],
# including other [].
a=(1 '2 3')
i=(0 1)
a[${i[1]}]=9
argv.py "${a[@]}"
# stdout: ['1', '9']

### Slice of array with [@]
# mksh doesn't support this syntax!  It's a bash extension.
a=(1 2 3)
argv.py "${a[@]:1:2}"
# stdout: ['2', '3']
# N-I mksh status: 1
# N-I mksh stdout-json: ""

### Negative slice
# mksh doesn't support this syntax!  It's a bash extension.
# NOTE: for some reason -2) has to be in parens?  Ah that's because it
# conflicts with :-!  That's silly.  You can also add a space.
a=(1 2 3)
argv.py "${a[@]:(-2):1}"
# stdout: ['2']
# N-I mksh status: 1
# N-I mksh stdout-json: ""

### Slice with arithmetic
a=(1 2 3)
i=5
argv.py "${a[@]:i-4:2}"
# stdout: ['2', '3']
# N-I mksh status: 1
# N-I mksh stdout-json: ""

### Number of elements
a=(1 '2 3')
echo "${#a[@]}"
# stdout: 2

### Iteration
a=(1 '2 3')
for v in "${a[@]}"; do
  echo $v
done
# stdout-json: "1\n2 3\n"

### glob within array yields separate elements
touch _tmp/y.Y _tmp/yy.Y
a=(_tmp/*.Y)
argv.py "${a[@]}"
# stdout: ['_tmp/y.Y', '_tmp/yy.Y']

### declare array and then append
declare -a array
array+=(a)
array+=(b c)
argv.py "${array[@]}"
# stdout: ['a', 'b', 'c']

### Array syntax in wrong place
ls foo=(1 2)
# status: 2
# OK mksh status: 1

### Empty array with :-
empty=()
argv.py ${empty[@]:-not one} "${empty[@]:-not one}"
# stdout: ['not', 'one', 'not one']

### Single array with :-
# bash does EMPTY ELISION here, unless it's double quoted.  Looks like mksh has
# the sane behavior.
single=('')
argv.py ${single[@]:-none} "${single[@]:-none}"
# stdout: ['none', '']
# OK mksh stdout: ['none', 'none']

### Stripping a whole array
files=('foo.c' 'sp ace.h' 'bar.c')
argv.py ${files[@]%.c} "${files[@]%.c}"
# stdout: ['foo', 'sp', 'ace.h', 'bar', 'foo', 'sp ace.h', 'bar']
# N-I mksh stdout-json: ""

### Multiple subscripts not allowed
a=('123' '456')
argv.py "${a[0]}" "${a[0][0]}"
# stdout-json: ""
# status: 2
# OK mksh status: 1
# bash is bad -- it IGNORES the bad subscript.
# BUG bash status: 0
# BUG bash stdout: ['123', '123']

### Length op, index op, then transform op is not allowed
a=('123' '456')
echo "${#a[0]}" "${#a[0]/1/xxx}"
# stdout-json: ""
# status: 2
# OK mksh status: 1
# bash is bad -- it IGNORES the op at the end
# BUG bash status: 0
# BUG bash stdout: 3 3

### Array subscript not allowed on string
s='abc'
echo ${s[@]}
# BUG bash/mksh status: 0
# BUG bash/mksh stdout: abc
# status: 1

### Create a "user" array out of the argv array
set -- 'a b' 'c'
array1=('x y' 'z')
array2=("$@")
array3="$@"  # Without splicing with (), this one is flattened
argv.py "${array1[@]}" "${array2[@]}" "${array3[@]}"
# stdout: ['x y', 'z', 'a b', 'c', 'a b c']

### Tilde expansion within array
HOME=/home/bob
a=(~/src ~/git)
echo "${a[@]}"
# stdout: /home/bob/src /home/bob/git

### Brace Expansion within Array
a=(-{a,b} {c,d}-)
echo "${a[@]}"
# stdout: -a -b c- d-

### array default
default=('1 2' '3')
argv.py "${undef[@]:-${default[@]}}"
# stdout: ['1 2', '3']


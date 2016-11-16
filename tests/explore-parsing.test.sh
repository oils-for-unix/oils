#!/bin/bash
#
# Tests that explore parsing corner cases.


### Bad env name: hyphen
# bash and dash disagree on exit code.
export FOO-BAR=foo
# status: 2
# OK bash/mksh status: 1

### Bad env name: period
export FOO.BAR=foo
# status: 2
# OK bash/mksh status: 1

### Bad var sub
echo $%
# stdout: $%

### Bad braced var sub -- not allowed
echo ${%}
# status: 2
# OK bash/mksh status: 1

### Bad var sub caught at parse time
if test -f /; then
  echo ${%}
else
  echo ok
fi
# status: 2
# BUG dash/bash/mksh status: 0

### Pipe with while
seq 3 | while read i
do
  echo ".$i"
done
# stdout-json: ".1\n.2\n.3\n"

### Length of length of ARGS!
func() { echo ${##}; }; func 0 1 2 3 4 5 6 7 8 
# stdout: 1

### Length of length of ARGS!  2 digit
func() { echo ${##}; }; func 0 1 2 3 4 5 6 7 8 9
# stdout: 2

### $1 .. $9 are scoped, while $0 is not
func() { echo $0 $1 $2 | sed -e 's/.*sh/sh/'; }; func a b
# stdout: sh a b

### Chained && and || -- || has higher precedence?
# It looks like expr 2 || expr 3 is evaluated at once.
expr 1 && expr 2 || expr 3 && expr 4; echo "result $?"
# stdout-json "1\n2\n4\nresult 0\n"

### Pipeline comments
echo abcd |    # input
               # blank line
tr a-z A-Z     # transform
# stdout: ABCD

### Command block
{ which ls; }
# stdout: /bin/ls

### { is its own word, needs a space
# dash gives 127; bash gives 2
{ls; }
# parse time error because of }
# status: 2
# runtime error
# OK mksh status: 1
# command not found for dash
# OK dash status: 127






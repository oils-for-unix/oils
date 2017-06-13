#!/bin/bash
#
# Tests that explore parsing corner cases.

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

### Chained && and || -- there is no precedence
expr 1 && expr 2 || expr 3 && expr 4
echo "status=$?"
# stdout-json: "1\n2\n4\nstatus=0\n"

### Pipeline comments
echo abcd |    # input
               # blank line
tr a-z A-Z     # transform
# stdout: ABCD

### Command block
{ which ls; }
# stdout: /bin/ls

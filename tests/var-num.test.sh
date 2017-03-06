#!/bin/bash
#
# Test $0 $1 $2

### Normal and braced
$SH -c 'echo $0 $1 ${2}' a b c d
# stdout: a b c

### In function
myfunc() {
  echo $1 ${2}
}
myfunc a b c d
# stdout: a b


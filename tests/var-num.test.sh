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

### $0 with -c
$SH -c 'echo $0' | grep -o 'sh$'
# stdout: sh

### $0 with stdin
echo 'echo $0' | $SH | grep -o 'sh$'
# stdout: sh

### $0 with -i
echo 'echo $0' | $SH -i | grep -o 'sh$'
# stdout: sh

### $0 with filename
s=_tmp/dollar0
echo 'echo $0' > $s
chmod +x $s
$SH $s
# stdout: _tmp/dollar0

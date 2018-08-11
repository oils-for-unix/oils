#!/usr/bin/env bash
#
# For testing the Python sketch

#### constant string
echo 'echo 1' | PS1='$ ' $SH --norc -i
## STDOUT:
$ 1
$ EOF when reading a line
## END

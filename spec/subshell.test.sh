#!/usr/bin/env bash

### Subshell exit code
( false; )
echo $?
# stdout: 1
# status: 0

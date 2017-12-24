#!/usr/bin/env bash

### Sourcing a script that returns is allowed no matter what
echo one
. spec/testdata/return-helper.sh
echo $?
echo two
# stdout-json: "one\nreturn-helper.sh\n42\ntwo\n"

### top level control flow
$SH spec/testdata/top-level-control-flow.sh
# stdout-json: "SUBSHELL\nBREAK\nCONTINUE\nRETURN\n"
# OK bash stdout-json: "SUBSHELL\nBREAK\nCONTINUE\nRETURN\nDONE\n"
# status: 0

### errexit and top-level control flow
$SH -o errexit spec/testdata/top-level-control-flow.sh
# stdout-json: "SUBSHELL\n"
# status: 2
# OK bash status: 1

### set -o strict-control-flow
$SH -o strict-control-flow -c 'echo break; break; echo hi'
# stdout: break
# status: 1
# N-I dash/bash status: 2
# N-I dash/bash stdout-json: ""
# N-I mksh status: 1
# N-I mksh stdout-json: ""

### return at top level is an error
return
echo "status=$?"
# stdout-json: ""
# OK bash stdout-json: "status=1\n"

### continue at top level is NOT an error
# NOTE: bash and mksh both print warnings, but don't exit with an error.
continue
echo status=$?
# stdout: status=0

### break at top level is NOT an error
break
echo status=$?
# stdout: status=0

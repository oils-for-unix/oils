#!/usr/bin/env bash

#### --debug-file
$SH --debug-file $TMP/debug.txt -c 'true'
grep 'Debug file' $TMP/debug.txt >/dev/null && echo yes
## stdout: yes

#### debug-completion option
set -o debug-completion
## status: 0

#### debug-completion from command line
$SH -o debug-completion
## status: 0

# NOTE: strict-arith has one case in arith.test.sh), strict-word-eval has a case in var-op-other.



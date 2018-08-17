#!/usr/bin/env bash

#### debug-line builtin
debug-line 'hi there'
## status: 0

#### debug-completion option
set -o debug-completion
## status: 0

#### debug-completion from command line
$SH -o debug-completion
## status: 0

# NOTE: strict-arith has one case in arith.test.sh), strict-word-eval has a case in var-op-other.



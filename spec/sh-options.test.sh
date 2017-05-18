#!/bin/bash
#
# Test set flags, sh flags.

### nounset
echo "[$unset]"
set -o nounset
echo "[$unset]"
echo end  # never reached
# stdout: []
# status: 1
# OK dash status: 2

### -u is nounset
echo "[$unset]"
set -u
echo "[$unset]"
echo end  # never reached
# stdout: []
# status: 1
# OK dash status: 2

### reset option with long flag
set -o errexit
set +o errexit
echo "[$unset]"
# stdout: []
# status: 0

### reset option with short flag
set -u 
set +u
echo "[$unset]"
# stdout: []
# status: 0

### sh -c
$SH -c 'echo hi'
# stdout: hi
# status: 0

### -n for no execution (useful with --ast-output)
# NOTE: set +n doesn't work because nothing is executed!
echo 1
set -n
echo 2
set +n
echo 3
# stdout-json: "1\n"
# status: 0

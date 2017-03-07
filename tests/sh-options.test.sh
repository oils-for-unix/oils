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

### sh -c
$SH -c 'echo hi'
# stdout: hi
# status: 0

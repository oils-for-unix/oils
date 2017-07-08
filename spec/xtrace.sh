#!/usr/bin/env bash
#
# Usage:
#   ./xtrace.sh <function name>

set -x

# all shells trace this badly.  They print literal newlines, which I don't
# want.
echo $'[\r\n]'

"$@"

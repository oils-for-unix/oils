#!/bin/sh
#
# Usage:
#   demo/fd-number.sh 8       # use FD 8
#   demo/fd-number.sh 100     # use FD 100
#   demo/fd-number.sh 1024    # use FD 1024
#   demo/fd-number.sh 1024 T  # use FD 1024, but RAISE default ulimit to allow it
#
# Derived from Andriy's example:
#
#   exec 25>out
#   echo hello>&25
#   cat out
#
# Except we generalize the FD number with 'eval'

set -o errexit

fd=${1:-8}
set_ulimit=${2:-}

# raise limit if necessary
if test -n "$set_ulimit"; then
  ulimit -n "$(( fd + 2 ))"  # +2 needed, not just +1 ?
fi

eval "exec $fd> _tmp/hello"
echo "using fd $fd" >& $fd
cat _tmp/hello

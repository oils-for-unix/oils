#!/bin/bash
#
# Usage:
#   ./14-parse-order.sh <function name>

# Hm bash is the only one that does parsing of $() during execution!  It
# doesn't report any errors here.

if test -f /; then
  echo $( ; )
  echo hi
fi


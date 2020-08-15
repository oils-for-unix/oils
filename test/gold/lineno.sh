#!/bin/bash
#
# Usage:
#   ./lineno.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

# https://unix.stackexchange.com/questions/355965/how-to-check-which-line-of-a-bash-script-is-being-executed

# This is different than LINENO, see gold/xtrace1.sh.

f(){ echo "${BASH_LINENO[-2]}"; }

echo next1
f

echo next2
f

echo next 3
f

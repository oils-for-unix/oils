#!/bin/bash
#
# Usage:
#   ./03-glob.sh <function name>

# Evaluates to command and arg
tests/echo.s[h-j]

# Negation
tests/echo.s[!i-z]
tests/echo.s[!i]

tests/echo.*

tests/echo.s?

# NOTE: bash also has extglob
# http://mywiki.wooledge.org/glob
#
# nullglob -- non-matching arguments get expand to nothing
# failglob -- non-matching arguments are an error
# dotglob -- dot files are matched
# globstar -- ** for directories

echo classes
tests/echo.s[[:alpha:]]

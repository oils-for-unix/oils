#!/usr/bin/env bash
#
# Usage:
#   ./03-glob.sh <function name>

# Evaluates to command and arg
spec/testdata/echo.s[h-j]

# Negation
spec/testdata/echo.s[!i-z]
spec/testdata/echo.s[!i]

spec/testdata/echo.*

spec/testdata/echo.s?

# NOTE: bash also has extglob
# http://mywiki.wooledge.org/glob
#
# nullglob -- non-matching arguments get expand to nothing
# failglob -- non-matching arguments are an error
# dotglob -- dot files are matched
# globstar -- ** for directories

echo classes
spec/testdata/echo.s[[:alpha:]]

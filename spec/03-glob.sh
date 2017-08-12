#!/usr/bin/env bash
#
# Usage:
#   ./03-glob.sh <function name>

# Evaluates to command and arg
spec/echo.s[h-j]

# Negation
spec/echo.s[!i-z]
spec/echo.s[!i]

spec/echo.*

spec/echo.s?

# NOTE: bash also has extglob
# http://mywiki.wooledge.org/glob
#
# nullglob -- non-matching arguments get expand to nothing
# failglob -- non-matching arguments are an error
# dotglob -- dot files are matched
# globstar -- ** for directories

echo classes
spec/echo.s[[:alpha:]]

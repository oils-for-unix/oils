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

# Geez this is lame

# "In addition to the traditional globs (supported by all Bourne-family shells)
# that we've seen so far, Bash (and Korn Shell) offers extended globs, which
# have the expressive power of regular expressions. Korn shell enables these by
# default; in Bash, you must run the command "

# ?(pattern-list): Matches empty or one of the patterns
# *(pattern-list): Matches empty or any number of occurrences of the patterns
# +(pattern-list): Matches at least one occurrences of the patterns
# @(pattern-list): Matches exactly one of the patterns
# !(pattern-list): Matches anything EXCEPT any of the patterns

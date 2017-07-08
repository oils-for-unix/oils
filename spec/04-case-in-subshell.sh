#!/usr/bin/env bash

foo=a
case $foo in [0-9]) echo number;; [a-z]) echo letter;; esac

# This works in bash, but syntax highlighting gets confused
out=$(case $foo in [0-9]) echo number;; [a-z]) echo letter;; esac)
echo $out

# OK multiline works
out=$(
echo a
echo b
)
echo $out

# This does NOT work in bash, even though it's valid.
#
# http://lists.gnu.org/archive/html/bug-bash/2016-03/msg00065.html
# Workarounds:
# - append semicolon behind first 'esac', or
# - insert any command line between the case statements, or
# - use `...` instead of $(...)

out=$(
case $foo in
  [0-9]) echo number;;
  [a-z]) echo letter;;
esac
case $foo in
  [0-9]) echo number;;
  [a-z]) echo letter;;
esac
)
echo $out



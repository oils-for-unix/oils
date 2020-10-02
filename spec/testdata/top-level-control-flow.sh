#!/usr/bin/env bash

# Hm this changes everything -- exit code is 1!
#set -o errexit

# Inspired by sources/download_functions.sh in Aboriginal:

#  wget -t 2 -T 20 -O "$SRCDIR/$FILENAME" "$1" ||
#      (rm -f "$SRCDIR/$FILENAME"; return 2)
 
# This also causes a warning, but is not fatal.
# bash gives a warning but mksh doesn't.
echo SUBSHELL
false || (rm -f foo; return 2)

echo BREAK
break
echo CONTINUE
continue

echo RETURN
# dash returns, bash warns that it's invalid.
# mksh returns.
return  # This is like exit?

# Bash gets here.
echo DONE

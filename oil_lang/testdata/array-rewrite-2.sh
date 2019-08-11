#!/bin/bash
#
# Example of rewriting string-based argv processing to use arrays.
#
# Adapted from ./linux-4.8.7/scripts/link-vmlinux.sh

# Show args to a command
argv() { spec/bin/argv.py "$@"; }

#
# OLD, BASH-COMPATIBLE WAY
#
# This style can't handle paths with spaces

CONFIG_HAVE_FOO=yes
path='/etc/path with spaces'
flags=''


if [ -n "${CONFIG_HAVE_FOO}" ]; then
  flags="${flags} --foo=$path"
fi

if [ -n "${CONFIG_HAVE_BAR}" ]; then
  flags="${flags} --bar"
fi

argv ${flags}  # unquoted splitting


#
# NEW OIL WAY
#
# - no quoting is necessary because of static-word-eval
# - splice arrays with @
# - builtin 'push' for appending
#   - I might want to change the ignored delimiter character _ to something like
#     : or :: or \\ .  Opinions?

shopt -s oil-parse-at static-word-eval

var CONFIG_HAVE_FOO = "yes"  # TODO: change to single quotes
var path = "/etc/path with spaces"
var flags = @()

if test -n $CONFIG_HAVE_FOO; then
  push flags _ --foo=$path
fi

if test -n $CONFIG_HAVE_BAR; then
  push flags _ --bar
fi

argv @flags

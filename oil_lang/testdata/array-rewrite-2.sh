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

set -o errexit
shopt -s parse_at simple_word_eval

setvar CONFIG_HAVE_FOO = "yes"  # TODO: change to single quotes
setvar path = "/etc/path with spaces"
setvar flags = @()

if test -n $CONFIG_HAVE_FOO; then
  push :flags --foo=$path
fi

if test -n $CONFIG_HAVE_BAR; then
  push :flags --bar
fi

argv @flags

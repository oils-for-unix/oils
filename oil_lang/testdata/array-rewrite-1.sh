#!/bin/bash
#
# Example of Oil arrays.
#
# Adapted from ./linux-4.8.7/scripts/tags.sh

# Show args to a command
argv() { spec/bin/argv.py "$@"; }

#
# OLD, BASH-COMPATIBLE WAY
#

regex=('one' 'two')
flags=()

for r in "${regex[@]}"; do
  flags[${#flags[@]}]="--regex=$r"
done

argv "${flags[@]}"


#
# NEW OIL WAY
#
# Things fixed:
# - verbose "${a[@]}" becomes @a
# - a=() is weird because it doesn't allow spaces around =
# - builtin 'push' for appending
#

shopt -s static-word-eval oil-parse-at

var regex2 = @(two three)
var flags2 = @()

for r in @regex2; do
  push flags2 _ "--regex=$r"
done

argv @flags2

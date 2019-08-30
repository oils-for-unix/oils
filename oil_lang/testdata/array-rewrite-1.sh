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

regex=(old1 old2)
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
#   - Oil uses var a = @()
# - builtin 'push' for appending
#

shopt -s simple_word_eval parse_at

var regex2 = @(new1 new2)
var flags2 = @()

for r in @regex2; do
  push :flags2 "--regex=$r"
done

argv @flags2

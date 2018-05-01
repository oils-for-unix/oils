#!/bin/bash
#
# Demo of bash completion fallback.  Hm.  -D is not chained, and neither is -F
# -F.
#
# Usage:
#   $ bash --norc --noprofile
#   $ . completion-demo.bash 

# NOOP
fnone() {
  echo -n ''
}

f12() {
  COMPREPLY=(f1 f2)
}

f34() {
  COMPREPLY=(f3 f4)
}

complete-file() {
  local cur="${COMP_WORDS[COMP_CWORD]}"
  # Hm no trailing slash here.
  COMPREPLY=( $(compgen -A file -- "${cur}") )
}

# Use -X to filter
complete-sh() {
  local cur="${COMP_WORDS[COMP_CWORD]}"
  # Hm no trailing slash here.
  COMPREPLY=( $(compgen -A file -X '!*.sh' -o plusdirs -- "${cur}") )
}

# default completion
complete -F f12 -F f34 -D

# empty completion
# Oops, does NOT fall back on f34
complete -F f12 -F f34 -F fnone -E

# Directory names will be completed with trailing slash; this is default readline behavior.
complete -A file foo

# Hm no trailing slash here.  Lame.
complete -F complete-sh bar

# Aha!  This adds trailing slash.  The problem is that if you are completing
# with -D, you may or may not be completing with a file!  Need to use comopt?
complete -F complete-sh -o filenames -o bashdefault barf

echo 'Installed completions'


#!/bin/bash
#
# Usage:
#   ./complete.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

audit() {
  local file=${1:-testdata/completion/git-completion.bash}

  echo
  echo --
  # Search for completion builtin usage
  grep -E -w --color 'complete|compgen|compopt' $file

  echo
  echo --
  # Search for special complation var usage
  grep -E --color 'COMP_[A-Z]+' $file

  echo
  echo --
  # Search for array usage
  grep -E --color ']=' $file
  grep -E --color ']+=' $file
}

audit-git() {
  audit
}


# NOTE: there are a number of associative arrays in completion scripts.
# e.g. localectl
#        local -A VERBS=(
#               [STANDALONE]='status list-locales list-keymaps'

audit-distro() {
  local path=/usr/share/bash-completion/bash_completion
  audit $path

  find /usr/share/bash-completion/ -type f | xargs grep -E --color ']\+?='
}

# Git completion is very big!
#
#   1528 /usr/share/bash-completion/completions/nmcli
#   1529 /usr/share/bash-completion/completions/svn
#   1995 /usr/share/bash-completion/bash_completion
#   2774 /usr/share/bash-completion/completions/git
#  39354 total

list-distro() {
  find /usr/share/bash-completion/ -type f | xargs wc -l | sort -n
}

"$@"

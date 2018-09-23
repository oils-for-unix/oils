#!/bin/bash
#
# Usage:
#   ./complete.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

readonly BASH_COMP=/usr/share/bash-completion/bash_completion.osh
readonly GIT_COMP=testdata/completion/git-completion.bash

audit() {
  local file=${1:-$GIT_COMP}

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

# After running this, source testdata/completion/git-completion.bash
fresh-osh-with-dump() {
  env -i OSH_CRASH_DUMP_DIR=_tmp  \
    bin/osh --debug-file _tmp/debug "$@"
}

osh-trace() {
  env -i OSH_CRASH_DUMP_DIR=_tmp PS4='+${LINENO} ' \
    bin/osh -x --debug-file _tmp/debug "$@"
}

bash-completion() {
  # This is a patched version
  fresh-osh-with-dump $BASH_COMP
}

bash-completion-trace() {
  osh-trace $BASH_COMP
}

# This should do nothing
git-completion() {
  fresh-osh-with-dump $GIT_COMP
}

git-completion-trace() {
  osh-trace $GIT_COMP
}

# See what completion is there by default.  It looks like filename completion.
# Actually it does complete variables with $ and ${.
bare-bash() {
  bash --noprofile --norc "$@"
}

"$@"

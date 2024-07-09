# oil-polyfill.sh
#
# Portable shell for some of Oil's builtins.
#
# Usage:
#   source oil-polyfill.sh

sh-strict() {
  ### Turn on "legacy" shell strict modes.

  # bash has this option, which is similar.
  # use || true in case 
  # Actually we don't need this because of static-word-eval subsumes it?
  #shopt -s nullglob 2>/dev/null || true

  # POSIX
  set -o errexit -o nounset -o pipefail

  # shopt
}

# Idea: from Soil, to fix Bernstein chaining.
#
# ssh $USER@$HOST "$(printf '%q ' "$@")"
#
# Also need one for scp.

# Idea: from tea/run.sh, exit 255 for xargs
# Does this need run --assign-status, or can it be POSIX shell?

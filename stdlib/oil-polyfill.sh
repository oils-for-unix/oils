# oil-polyfill.sh
#
# Portable shell for some of Oil's builtins.
#
# Usage:
#   source oil-polyfill.sh
#
# TODO: Where to deploy this?  I think we want versioned copies in
# ~/.local/lib/oil-0.7.0/stdlib/oil-polyfill.sh

sh-strict() {
  ### Turn on "legacy" shell strict modes.

  # bash has this option, which is similar.
  # use || true in case 
  # Actually we don't need this because of static-word-eval subsumes it?
  #shopt -s nullglob 2>/dev/null || true

  # POSIX
  set -o errexit -o nounset -o pipefail
}

log() {
  ### Write a message to stderr.
  echo "$@" 1>&2
}

die() {
  ### Write a message to stderr and exit failure.
  log 'fatal:' "$@"
  exit 1
}

# Idea: from services/travis.sh, to fix Bernstein chaining.
#
# ssh $USER@$HOST "$(printf '%q ' "$@")"
#
# Also need one for scp.

# Two functions I actually use, all the time.
#
# To keep depenedencies small, this library will NEVER grow other functions
# (and is named to imply that.)
#
# Usage:
#   source --builtin two.sh
#
# Examples:
#    log 'hi'
#    die 'expected a number'

if command -v source-guard >/dev/null; then  # include guard for YSH
  source-guard two || return 0
fi

log() {
  ### Write a message to stderr.
  echo "$@" >&2
}

die() {
  ### Write an error message with the script name, and exit with status 1.
  log "$0: fatal: $@"
  exit 1
}


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

log() {
  ### Write a message to stderr.
  echo "$@" >&2
}

die() {
  ### Write an error message with the script name, and exit failure.
  log "$0: fatal: $@"
  exit 1
}


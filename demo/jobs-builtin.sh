#!/usr/bin/env bash
#
# Compare the output of "jobs" in different shells
#
# Usage:
#   $SH demo/jobs-builtin.sh <function name>

set -o nounset
#set -o pipefail
set -o errexit

# Notes:
# - the formats are consistent, because it's specified by POSIX
#   - they use [1] [2] [3] 
#   - + is the default job for 'fg' and 'bg', which is also %%
#   - - is the job that would become the default, which is also %-
#
# "[%d] %c %s %s\n", <job-number>, <current>, <state>, <command>
#
# https://pubs.opengroup.org/onlinepubs/9699919799/utilities/jobs.html
#
# TODO: Oil should print this as QSN!   So you can parse it.
#
# - dash is the only shell that doesn't show source code; it just shows | for pipe
# - mksh has some weird quoting, like \sleep 1
# - mksh and zsh doesn't show trailing &, but bash does
#

show_jobs() {
  echo ___

  # all shells support this long format which shows components of a pipeline
  jobs -l
  #jobs
}

myfunc() {
  sleep 0.3
  show_jobs

  sleep 0.4
  show_jobs
}


demo() {
  sleep 1 & sleep 2 & 
  show_jobs

  { echo pipe1; sleep 0.5; } | cat &
  show_jobs

  myfunc &

  # only bash supports wait -n
  if test -n "${BASH_VERSION:-}"; then
    wait -n
    show_jobs
  fi

  wait
  show_jobs

  ls | wc -l
  show_jobs
}

"$@"

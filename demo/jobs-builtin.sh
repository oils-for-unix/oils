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
# TODO: YSH should print this as J8!   So you can parse it.
#
# - dash is the only shell that doesn't show source code; it just shows | for pipe
# - mksh has some weird quoting, like \sleep 1
# - mksh and zsh doesn't show trailing &, but bash does
#

show_jobs() {
  echo ___

  # all shells support this long format which shows components of a pipeline
  #if true; then
  if true; then
    jobs -l
  else
    jobs
  fi
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

  # In jobs -l, bash, zsh, and mksh all combine this onto one line:
  # { echo pipe1; sleep 0.5; }

  { echo pipe1
    sleep 0.5
  } | tac | wc -l &

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

many_jobs() {
  sleep 0.90 &
  sleep 0.91 &
  sleep 0.92 &
  sleep 0.93 &
  sleep 0.94 &
  sleep 0.95 &
  sleep 0.96 &
  sleep 0.97 &
  sleep 0.98 &
  sleep 0.99 &

  show_jobs

  # Testing this syntax
  # Doesn't work because shells say "job %10 not created under job control"
  # fg %10

  wait
  show_jobs
}

osh-debug() {
  # lastpipe with 'read'
  { echo x; sleep 0.1; } | sort | read x
  jobs --debug

  # no lastpipe
  { echo x; sleep 0.1; } | sort | wc -l
  jobs --debug
}

"$@"

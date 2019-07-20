#!/usr/bin/env bash
set -euo pipefail

read-one () {
  # try typing a letter without hitting newline
  # the shell should respond immediately
  read -n 1
  echo
  echo "$REPLY"
}

read-multiple () {
  read -n 5
  echo
  echo "$REPLY"
}

all () {
  echo "one char:"
  read-one
  echo "multiple chars:"
  read-multiple
}

"$@"

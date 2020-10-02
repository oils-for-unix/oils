#!/usr/bin/env bash

detect_readline() {
  echo foo >/dev/null 2>&1
  echo "two" 1>&2
}

main() {
  detect_readline > _tmp/f2-out.txt
  #detect_readline 
}

main "$@"

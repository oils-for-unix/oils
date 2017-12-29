#!/usr/bin/env bash
#
# For spec/introspect.test.sh.

source spec/testdata/bash-source-2.sh

argv() {
  spec/bin/argv.py "$@"
}

f() {
  argv 'begin F funcs' "${FUNCNAME[@]}" 
  argv 'begin F files' "${BASH_SOURCE[@]}" 
  argv 'begin F lines' "${BASH_LINENO[@]}" 
  g
  argv 'end F funcs' "${FUNCNAME[@]}" 
  argv 'end F' "${BASH_SOURCE[@]}"
  argv 'end F lines' "${BASH_LINENO[@]}" 
}

f  # call a function it defines

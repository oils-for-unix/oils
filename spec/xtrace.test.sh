#!/usr/bin/env bash
#
# xtrace test.  Test PS4 and line numbers, etc.
#
# TODO: need multiline test format

### basic xtrace
set -x
echo one >&2
echo two >&2
# stdout-json: ""
# stderr-json: "+ echo one\none\n+ echo two\ntwo\n"

### xtrace
echo 1
set -o xtrace
echo 2
# stdout-json: "1\n2\n"
# stderr: + echo 2

### PS4 is scoped
set -x
echo one
f() { 
  local PS4='- '
  echo func;
}
f
echo two
# stderr-json: "+ echo one\n+ f\n+ local 'PS4=- '\n- echo func\n+ echo two\n"

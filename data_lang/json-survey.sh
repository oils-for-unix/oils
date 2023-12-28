#!/usr/bin/env bash
#
# Usage:
#   data_lang/json-survey.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source build/dev-shell.sh  # python3 in $PATH

int-float() {
  # This is a float
  python2 -c 'import json; val = json.loads("1e6"); print(type(val)); print(val)'
  python2 -c 'import json; val = json.loads("1e-6"); print(type(val)); print(val)'
  python2 -c 'import json; val = json.loads("0.5"); print(type(val)); print(val)'

  # Int
  python2 -c 'import json; val = json.loads("42"); print(type(val)); print(val)'

  python3 -c 'import json; val = json.loads("1e6"); print(type(val)); print(val)'

  echo
  echo

  # JavaScript only has 'number', no Int and Float
  nodejs -e 'var val = JSON.parse("1e6"); console.log(typeof(val)); console.log(val)'
}

syntax-errors() {

  python2 -c 'import json; val = json.loads("{3:4}"); print(type(val)); print(val)' || true
  echo
  python2 -c 'import json; val = json.loads("[3:4]"); print(type(val)); print(val)' || true

  echo
  echo

  # This has good position information
  # It prints the line number, the line, and points to the token in the line
  # where the problem happened

  nodejs -e 'var val = JSON.parse("{3: 4}"); console.log(typeof(val)); console.log(val)' || true

  nodejs -e 'var val = JSON.parse("[\n  3: 4\n]"); console.log(typeof(val)); console.log(val)' || true

  nodejs -e 'var val = JSON.parse("[\n\n \"hello "); console.log(typeof(val)); console.log(val)' || true
}

empty-input() {
  python3 -c 'import json; val = json.loads(""); print(type(val)); print(val)' || true

  echo
  echo

  nodejs -e 'var val = JSON.parse(""); console.log(typeof(val)); console.log(val)' || true
}

obj-cycles() {
  python3 -c 'import json; val = {}; val["k"] = val; print(json.dumps(val))' || true
  echo

  # Better error message than Python!
  # TypeError: Converting circular structure to JSON
  #  --> starting at object with constructor 'Object'
  #  --- property 'k' closes the circle
  nodejs -e 'var val = {}; val["k"] = val; console.log(JSON.stringify(val))' || true
}

"$@"

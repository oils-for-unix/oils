#!/bin/bash
#
# Usage:
#   ./type.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

install-pip3() {
  sudo apt-get install python3-pip
}

install-mypy() {
  sudo pip3 install mypy-lang
}

demo() {
  #mypy core/oil_main.py  # token errors

  # Doesn't like dynamic TN enum
  #mypy core/arith_node.py
  mypy core/bool_node.py
  mypy core/cmd_node.py
  mypy core/word_node.py

  mypy core/builtin.py
  mypy core/process.py
  return
  #mypy core/completion.py

  mypy core/lexer.py

  mypy core/arith_eval.py
  #mypy core/bool_eval.py  # problem with libc

  mypy core/base.py
  return

  #mypy core/tdop.py
  #mypy core/sh_arith_parse.py
  #mypy core/cmd_parse.py
  return

  #mypy gen_tokens.py
  mypy core/tokens.py
  mypy core/reader.py
}

"$@"

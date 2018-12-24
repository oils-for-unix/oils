#!/bin/bash
#
# See if mypy's pyi format is useful.  It does extract members.
#
# Usage:
#   ./pyi.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

install() {
  # needs
  pip3 install mypy
}

oil-stubgen() {
  local module=$1
  local out=_tmp/pyi
  PYTHONPATH=. _OVM_RESOURCE_ROOT=. ~/.local/bin/stubgen --py2 -o $out $module
}

demo() {
  local out=_tmp/pyi
  mkdir -p $out
  # core/util.py respects that
  oil-stubgen bin.oil
  #oil-stubgen osh/cmd_parse
}

# Also used in test/wild.sh
multi() { ~/hg/tree-tools/bin/multi "$@"; }

manifest() {
  # TODO: Should change build/app_deps.py
  local out=_tmp/mypy
  mkdir -p $out
  PYTHONPATH=. build/app_deps.py py-manifest bin.oil | multi cp $out
}

stubgen-path() {
  local py_path=$1
  module=${py_path%'.py'}  # strip suffix
  module=${module//'/'/.}  # turn / to .
  echo "stubgen $module"

  local out=_tmp/pyi

  # Hm somehow this causes a syntax error.

  #PYTHONPATH=_tmp/mypy _OVM_RESOURCE_ROOT=. ~/.local/bin/stubgen --py2 -o $out $module
  PYTHONPATH=. _OVM_RESOURCE_ROOT=. ~/.local/bin/stubgen --py2 -o $out $module
}

stubgen-all() {
  find _tmp/mypy -name '*.py' -a -printf '%P\n' \
    | grep -v stat | xargs -n 1 -- $0 stubgen-path
}

show() {
  # issue: you get 'log'
  find _tmp/pyi -name '*.pyi' | xargs wc -l
  find _tmp/pyi -name '*.pyi' | xargs head -n 10
}

"$@"

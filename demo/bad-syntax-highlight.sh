#!/usr/bin/env bash
#
# Where does Vim fail to highlight shell correctly?
#
# Usage:
#   ./bad-syntax-highlight.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

# There is a list of recent bugs in sh.vim
# https://github.com/vim/vim/blob/master/runtime/syntax/sh.vim
#
# Could test emacs and other editors too

multiple-here-docs() {
  # the second here doc isn't right
  diff -u /dev/fd/3 /dev/fd/4 3<<EOF3 4<<EOF4
foo
EOF3
bar
EOF4
}

command-sub-case() {
  # parens aren't right
  echo $(case foo in foo) echo hi ;; esac)
}

"$@"

#!/usr/bin/env bash
#
# Run tools to maintain the coding style.
#
# Usage:
#   devtools/repo.sh <function name>

find-prune() {
  ### Filter out big dirs for speed

  find . \
    '(' -type d -a -name '_*' \
     -o -name testdata \
     -o -name Python-2.7.13 \
     ')' -a -prune \
     "$@"
}

find-src-files() {
  ### Find real source files

  # TODO: Add .R and .js

  find-prune \
    -o -type f -a \
   '(' -name '*.py' \
    -o -name '*.sh' \
    -o -name '*.asdl' \
    -o -name '*.[ch]' \
    -o -name '*.cc' \
   ')' -a -print 
}

# Similar to test/unit.sh
py-files() {
  find-prune -o -name '*.py' -a -printf '%P\n' | sort
}

py-manifest() {
  py-files | while read path; do
    read -r first_line < $path
    #echo $first_line
    if [[ $first_line == *python3* ]]; then
      kind=py3
      #py_path_more=:  # no-op
    else
      kind=py2
      #py_path_more=:vendor/  # for vendor/typing.py
    fi

    echo "$kind $path"
  done
}

"$@"

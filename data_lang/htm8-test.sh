#!/usr/bin/env bash
#
# Usage:
#   data_lang/htm8-test.sh

: ${LIB_OSH=stdlib/osh}
source $LIB_OSH/bash-strict.sh
source $LIB_OSH/task-five.sh

# parse with lazylex/html.py, or data_lang/htm8.py

site-files() {
  find ../../oilshell/oilshell.org__deploy -name '*.html'
}

# Issues with lazylex/html.py
# 
# - Token ID is annoying to express in Python
# - re.DOTALL for newlines
#   - can we change that with [.\n]*?
# - nongreedy match for --> and ?>


test-site() {
  # 1.5 M lines of HTML - takes 3 xargs invocations!
  # 
  # TODO: 
  # - test that it lexes
  # - test that tags are balanced

  site-files | xargs wc -l
}

test-wwz() {
  echo 'TODO: download .wwz from CI'
}

task-five "$@"

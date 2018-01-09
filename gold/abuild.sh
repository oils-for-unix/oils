#!/bin/bash
#
# Snippets from abuild that we need to run correctly.

is_function() {
  type "$1" 2>&1 | head -n 1 | egrep -q "is a (shell )?function"
}

"$@"

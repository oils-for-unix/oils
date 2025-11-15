#!/usr/bin/env bash
#
# Usage:
#   devtools/claude.sh <function name>
#
# Related:
#   https://github.com/oils-for-unix/oils/wiki/AI-Contribution-Policy 

set -o nounset
set -o pipefail
set -o errexit

install() {
  npm install @anthropic-ai/claude-code
}

run() {
  # for locally installed stuff
  npx claude
}

show-junk() {
  # Too much junk!  They should have confined it to one dir

  tree ~/.claude
  echo

  ls -l ~/.claude.*
}

"$@"

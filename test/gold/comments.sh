#!/usr/bin/env bash
#
# Usage:
#   ./comments.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

main() {
  # N
  echo foo\
#not_comment

  echo "foo\
#not_comment"

  echo "foo\
 #not_comment"
}

main "$@"

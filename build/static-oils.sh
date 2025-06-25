#!/usr/bin/env bash
#
# Make a statically linked build.  Works with GNU libc and musl libc.
#
# Usage:
#   build/static-oils.sh

set -o nounset
set -o errexit

show_help() {
  echo '
Compile oils-for-unix and statically link it.

Usage:
   build/static-oils.sh

This is a one-line wrapper around _build/oils.sh.
'
}

parse_flags() {
  while true; do
    case "${1:-}" in
      -h|--help)
        show_help
        exit 0
        ;;
      -*)
        echo "Invalid flag '$1'" >& 2
        exit 2
        ;;
      *)
        # No more flags
        break
        ;;
    esac
    shift
  done
}


main() {
  parse_flags "$@"  # sets FLAG_*, or prints help

  LDFLAGS='-static' _build/oils.sh \
    --suffix '-static' --without-readline --skip-rebuild
}

main "$@"

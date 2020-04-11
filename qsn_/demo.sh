#!/bin/bash
#
# What do Unix tools do with "bad" filenames?
#
# - Those with invalid unicode
# - Those with terminal escape sequences
#
# Usage:
#   qsn/demo.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

# We already know:
# - bash ${#len} operator is very broken
#
# Suggestion:
#  QSN should be printf %q !!!  In ANSI C.

# in bash it could be %Q.  Or maybe it's %Q everywhere?
# in mycpp, we can translate %r calling repr() to qsn::encode()


# Summary:
#
# These tools do UTF-8 error decoding, but they use a funny shell-like format:
#
# - GNU coreutils: ls, cp, stat
# - GNU tar
# - zsh in error message, and in printf %q
# - bash and mksh in printf %q only, but not in error message
# - GNU findutils: find, but NOT xargs
#
# Surprise: not grep
#
# TODO: automate this a bit?
# - You can validate their stdout and stderr?
#   - Look for the literal escape sequence.


# TODO: What about the one that changes the title?

BOLD=$'\x1b[1m'
RESET=$'\x1b[0;0m'

# A mix of valid and invalid utf-8
char_then_byte=$'\xce\xce\xbc'
byte_then_char=$'\xce\xbc\xce'

readonly DIR=_tmp/qsn-demo

banner() {
  echo
  echo =====
  echo "$@"
  echo
}

setup-bad-files() {

  # - Make a file with an invalid code point, and utf-8 char
  # - Make a file with a terminal escape sequence

  mkdir -p $DIR
  pushd $DIR
  touch -- $BOLD $char_then_byte $byte_then_char
}

test-programs() {
  echo "$BOLD Hello $RESET World"

  # does approximate decoding
  printf '%q\n' "$char_then_byte"
  printf '%q\n' "$byte_then_char"

  setup-bad-files
  # ls doesn't print these by default, that' sgood

  # Hm this also does approximate decoding
  banner 'ls'
  ls 
  echo
  ls --escape
  echo
  # Test out error message
  # It's basicallly correct, but ugly.  There are too many segments, and
  # there's an unnecessary leading ''.
  # QSN is shorter and more consistent.

  ls -- "$RESET" || true

  # same
  banner 'cp'
  cp -- "$RESET" /tmp || true

  # weird output but it ultimately understands it
  banner 'stat'
  stat *

  # Hm also understands utf-8
  banner 'find'
  find
  # This prints it raw
  #find -print0

  # xargs --verbose messes up!  Makes it bold.  It also understands less
  # unicode.
  if false; then
    banner 'xargs'
    echo * | xargs --verbose -n 1 -- true
  fi

  # prints bytes, no unicode
  banner 'strace'
  strace -- true "$BOLD" "$char_then_byte" "$byte_then_char"

  # it does understand mu
  banner 'ps'
  bash -c "true zzmagic $BOLD $char_then_byte $byte_then_char; sleep 2" &
  ps aux | grep zzmagic
}

test-errors() {
  # also prints it
  setup-bad-files

  # GOOD
  banner 'tar'
  tar -f $BOLD || true
  tar --create "$BOLD" "$byte_then_char" "$char_then_byte" > out.tar
  tar --list < out.tar

  banner 'rm'
  # works
  rm -f -v -- "$BOLD" "$byte_then_char" "$char_then_byte"

  banner 'grep'
  # BUG
  #grep z "$BOLD"
  grep z "$byte_then_char" || true
  grep z "$char_then_byte" || true

  # python doens't print it smehow?
  banner 'python'
  # BUG: Python prints terminal sequences
  #python "$BOLD" || true
  python "$byte_then_char" || true
  python "$char_then_byte" || true

  # BUG: Lua prints terminal sequences
  # So coreutils does it right!
  banner 'lua'
  #lua "$BOLD" || true
  lua "$byte_then_char" || true
  lua "$char_then_byte" || true

  # BUG: prints it
  banner 'awk'
  #awk -F "$BOLD" || true
  awk -F "$byte_then_char" || true
  awk -F "$char_then_byte" || true

  # BUG
  banner 'ruby'
  #ruby "$BOLD" || true
  ruby "$byte_then_char" || true
  ruby "$char_then_byte" || true

  # BUG
  banner 'perl'
  #perl "$BOLD" || true
  perl "$byte_then_char" || true
  perl "$char_then_byte" || true

  # BUG
  # But it's a little smarter about mu cases
  banner 'nodejs'
  #nodejs "$BOLD" || true
  nodejs "$byte_then_char" || true
  nodejs "$char_then_byte" || true

  # shells:

  # BUG
  banner 'bash'
  #bash "$BOLD" || true
  bash "$byte_then_char" || true
  bash "$char_then_byte" || true

  banner 'dash'
  #dash "$BOLD" || true

  # zsh actually escapes it!
  banner 'zsh'
  zsh "$BOLD" || true
  zsh "$byte_then_char" || true
  zsh "$char_then_byte" || true

  # BUG
  banner 'mksh'
  #mksh "$BOLD" || true
}

test-busybox() {
  setup-bad-files

  # displays ?? -- doesn't understand unicode
  banner 'busybox ls'
  busybox ls 

  # BUG: prints it literally
  banner 'busybox find'
  busybox find

  #reset
}

"$@"

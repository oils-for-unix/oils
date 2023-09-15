#!/usr/bin/env bash
#
# Function to generate tags files, e.g. for Vim Ctrl-] lookup.
#
# Usage:
#   devtools/ctags.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

ubuntu-deps() {
  sudo apt install exuberant-ctags
}

# Creates a 9 MB file.
index-python() {
  pushd Python-2.7.13/
  ctags --recurse
  ls -l tags
  popd
}

oils-ctags-out() {

  # Vim complains unless we have this
  echo $'!_TAG_FILE_SORTED\t0'

  # We want an explicit manifest to avoid walking _chroot/ and so forth.  ctags
  # --exclude doesn't work well.

  test/lint.sh find-src-files | ctags --filter | sort 
}

index-oils() {
  time oils-ctags-out > tags

  # This file ends up at 992 KB
  # It's 11832 symbols/lines
  # That's way too many; doesn't work that well
  # Comment/string/def lexers should do better

  ls -l tags
}

# TODO:
#
# The ctags file is easy to generate!
#
# - Select the list of files
# - SYMBOL \t FILENAME \t VI-COMMAND ;" EXTENSION
#   - you can just use a line number?
#   - well then it's out of date if you insert something, so that's why they
#     use /
#
# Intermediate format - OTAGS
# - SYMBOL FILENAME LINE
#   - and then GENERATE ctags from this - with /^ command.  I guess you escape \/
#   - GENERATE HTML or JSON from this
#     - you can have a big list of symbols to highlight
#
# - osh --tool ctags FILE*
#   - warn about duplicates
#
# Idea for comment/string/def lexers, i.e. CSD:
#
# See devtools/README.md

"$@"

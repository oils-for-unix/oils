#!/bin/bash
#
# Usage:
#   ./complete.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

readonly BASH_COMP=../bash-completion/bash_completion

# This version is too new to run on my Ubuntu machine!  Uses git --list-cmds.
#readonly GIT_COMP=testdata/completion/git-completion.bash

readonly GIT_COMP=testdata/completion/git

grep-extglob() {
  grep -E --color '[@?!+*]\(' "$@"
}

# A very common case is something like:
#
# --host|-!(-*)h
#
# which matches --host, -h, -ah, but NOT --h.
#
# https://github.com/oilshell/oil/issues/192
grep-extglob-negation() {
  grep -E --color '!\(' $BASH_COMP ../bash-completion/completions/*
}

audit() {
  local file=${1:-$GIT_COMP}

  echo
  echo --
  # Search for completion builtin usage
  grep -E -w --color 'complete|compgen|compopt' $file

  echo
  echo --
  # Search for special complation var usage
  grep -E --color 'COMP_[A-Z]+' $file

  echo
  echo --
  # Search for array usage
  grep -E --color ']=' $file
  grep -E --color ']+=' $file

  # extended glob
  grep-extglob $file
}

audit-git() {
  audit
}

readonly COMPLETION_FILES=($BASH_COMP ../bash-completion/completions/*)

# EVERY plugin seems to use the _init_completion function.  We can do this
# ourselves!
audit-plugin-init() {
  ls ../bash-completion/completions/* | wc -l
  #grep -c _init_completion ../bash-completion/completions/* 

  # almost all calls are the same!
  # the -n changes delimiters.  Why would you need that?  Those need to be
  # rewritten?
  #
  # There is one instance of -o '@(diff|patch)
  # -s is for splitting longopt with --foo=
  # Oh OK maybe I should just implement that in Python in OSH?
  #
  # So everything is about the delimiters.

  grep --no-filename _init_completion "${COMPLETION_FILES[@]}" |
    sort | uniq -c | sort -n
}  

audit-plugin-x() {
  echo
  echo '-X usage'
  echo

  grep --no-filename -- -X "${COMPLETION_FILES[@]}"
}

# Hm I guess you could implement these two?  _get_cword and _get_pword can look
# at COMP_ARGV or 'words'?

# Yes they both take delimiters like -n.  So just take COMP_ARGV and split, and
# then get the last one or second to last.

audit-plugin-funcs() {
  echo
  echo 'annoying functions'
  echo

  # _get_cword and _get_pword should be easy to implement.  COMP_ARGV is split
  # with delimiters again.  Should you try an oracle?
  grep --color -- '_get_.word' "${COMPLETION_FILES[@]}"

  # This calls __reassemble_comp_words_by_ref
  grep --color -w -- '_count_args' "${COMPLETION_FILES[@]}"

  # These call _get_comp_words_by_ref, which calls _get_cword_at_cursor_by_ref,
  # which calls __reassemble_comp_words_by_ref
  grep --color -w -- '_command' "${COMPLETION_FILES[@]}"
  grep --color -w -- '_command_offset' "${COMPLETION_FILES[@]}"

  # Should be replaced by compgen -A file?
  grep --color -w -- '_filedir' "${COMPLETION_FILES[@]}"

  # What's the difference between these two?
  grep --color -w -- '_expand' "${COMPLETION_FILES[@]}"
  grep --color -w -- '_tilde' "${COMPLETION_FILES[@]}"
}

audit-bashcomp() {
  local path=$BASH_COMP

  audit $path

  # Some of these are not cash variables.
  grep -E -o 'COMP_[A-Z]+' $path | hist

  grep-extglob ../bash-completion/completions/*

  #find /usr/share/bash-completion/ -type f | xargs grep -E --color ']\+?='
}

# Git completion is very big!
#
#   1528 /usr/share/bash-completion/completions/nmcli
#   1529 /usr/share/bash-completion/completions/svn
#   1995 /usr/share/bash-completion/bash_completion
#   2774 /usr/share/bash-completion/completions/git
#  39354 total

list-distro() {
  find /usr/share/bash-completion/ -type f | xargs wc -l | sort -n
}

# After running this, source testdata/completion/git-completion.bash
fresh-osh-with-dump() {
  env -i OSH_CRASH_DUMP_DIR=_tmp  \
    bin/osh --debug-file _tmp/debug "$@"
}

osh-trace() {
  # $FUNCNAME displays the whole stack in osh (unlike bash), but ${FUNCNAME[0]}
  # displays the top.

  # NOTE: env -i disables $TERM, which breaks some things.
  #env -i 

  OSH_CRASH_DUMP_DIR=_tmp \
  OSH_HIJACK_SHEBANG=bin/osh \
    PS4='+[${LINENO}:${FUNCNAME[0]}] ' \
    bin/osh -x --debug-file _tmp/debug --xtrace-to-debug-file "$@"
}

osh-debug() {
  OSH_CRASH_DUMP_DIR=_tmp \
  OSH_HIJACK_SHEBANG=bin/osh \
    bin/osh --debug-file _tmp/debug "$@"
}

bash-bash() {
  PS4='+[${LINENO}:${FUNCNAME}] ' bash -x $BASH_COMP
}

bash-completion() {
  # This is a patched version
  fresh-osh-with-dump $BASH_COMP
}

bash-completion-trace() {
  osh-trace $BASH_COMP
}

# This should do nothing
git-completion() {
  fresh-osh-with-dump $GIT_COMP
}

git-completion-trace() {
  osh-trace $GIT_COMP
}

# See what completion is there by default.  It looks like filename completion.
# Actually it does complete variables with $ and ${.
bare-bash() {
  bash --noprofile --norc "$@"
}

# TODO: This is a good use case
npm-comp() {
  npm completion | bin/osh -n
  #npm-completion > _tmp/npm.sh
  #bin/osh -n _tmp/npm.sh
}

# NOTE: This package doesn't have git completion.  That comes with the git package!
download-bash-completion-xenial() {
  # binary package
  if false; then
    wget --directory _tmp \
      http://mirrors.kernel.org/ubuntu/pool/main/b/bash-completion/bash-completion_2.1-4.2ubuntu1_all.deb
  fi

  # source package
  wget --directory _tmp \
    http://archive.ubuntu.com/ubuntu/pool/main/b/bash-completion/bash-completion_2.1.orig.tar.bz2
}

# Conclusion: git-completion.bash is is unmodified.  It's just renamed to
# /usr/share/bash-completion/git.  It seems to use the _git() and _gitk() entry
# points.
download-git-package() {
  true || wget --directory _tmp \
    http://archive.ubuntu.com/ubuntu/pool/main/g/git/git_2.7.4.orig.tar.xz
  wget --directory _tmp \
    http://security.ubuntu.com/ubuntu/pool/main/g/git/git_2.7.4-0ubuntu1.6_amd64.deb
}

"$@"

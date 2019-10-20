#!/usr/bin/env bash
#
# Copied from my bashrc.

# TODO: The branch name isn't being displayed?
git-prompt() {
  . testdata/completion/git
  . ~/git-prompt.sh

  export PS1='\u@\h \w$(__git_ps1 " (%s)")\$ '
}

git-prompt


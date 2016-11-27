#!/bin/bash
#
# Run the osh parser on shell scripts found in the wild.
#
# TODO: There are a lot of hard-coded source paths here.  These files could
# published in a tarball or torrent.
#
# Usage:
#   ./wild.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

readonly RESULT_DIR=_tmp/wild

#
# Helpers
# 

osh-parse() {
  bin/osh --print-ast --no-exec "$@"
}

# TODO: err file always exists because of --no-exec
_parse-one() {
  local input=$1
  local output=$2

  echo $input

  local stderr_file=$output-err.txt
  osh-parse $input > $output-AST.txt 2> $stderr_file
  local status=$?

  return $status
}

_parse-and-copy-one() {
  local src_base=$1
  local dest_base=$2
  local rel_path=$3

  local input=$src_base/$rel_path
  local output=$dest_base/$rel_path

  if grep -E 'exec wish|exec tclsh' $input; then
    echo "$rel_path SKIPPED"

    local html="
    $rel_path SKIPPED because it has 'exec wish' or 'exec tclsh'
    <hr/>
    "
    echo $html >>$dest_base/FAILED.html
    return 0
  fi

  mkdir -p $(dirname $output)
  if ! _parse-one $input $output; then
    echo $rel_path >>$dest_base/FAILED.txt

    # Append
    local html="
    <a href=\"$rel_path.txt\">$rel_path.txt</a>
    <a href=\"$rel_path-err.txt\">$rel_path-err.txt</a>
    <a href=\"$rel_path-AST.txt\">$rel_path-AST.txt</a>
    <br/>
    <pre>
    $(cat $output-err.txt)
    </pre>
    <hr/>
    "
    echo $html >>$dest_base/FAILED.html
  fi
  #rm $output-err.txt

  # Add .txt extension so it's not executable, and use 'cat' instead of cp
  # So it's not executable.
  cat < $input > ${output}.txt
}

_parse-many() {
  local src_base=$1
  local dest_base=$2
  shift 2
  # Rest of args are relative paths

  # Truncate the failure
  mkdir -p $dest_base
  echo -n '' >$dest_base/FAILED.txt
  echo -n '' >$dest_base/FAILED.html

  for f in "$@"; do echo $f; done |
    sort |
    xargs -n 1 -- $0 _parse-and-copy-one $src_base $dest_base

  # PROBLEM that can be solved with tables:
  # using relative path to pass to wc -l
  # wc -l "$@" >

  { pushd $src_base >/dev/null
    wc -l "$@"
    popd >/dev/null
  } > $dest_base/LINE-COUNTS.txt

  tree -p $dest_base
}

# generic helper
_parse-project() {
  local src=$1
  local name=$(basename $src)

  time _parse-many \
    $src \
    $RESULT_DIR/$name-parsed \
    $(find $src -name '*.sh' -a -printf '%P\n')
}

_parse-configure-scripts() {
  local src=$1
  local name=$(basename $src)

  time _parse-many \
    $src \
    $RESULT_DIR/$name-configure-parsed \
    $(find $src -name 'configure' -a -printf '%P\n')
}

#
# Corpora
#

oil-sketch() {
  local src=~/git/oil-sketch
  _parse-many \
    $src \
    $RESULT_DIR/oil-sketch-parsed \
    $(cd $src && echo *.sh {awk,demo,make,misc,regex,tools}/*.sh)
}

this-repo() {
  local src=$PWD
  _parse-many \
    $src \
    $RESULT_DIR/oil-parsed \
    *.sh
}

readonly ABORIGINAL_DIR=~/src/aboriginal-1.4.5

parse-aboriginal() {
  # We want word splitting
  _parse-many \
    $ABORIGINAL_DIR \
    $RESULT_DIR/aboriginal-parsed \
    $(find $ABORIGINAL_DIR -name '*.sh' -printf '%P\n')
}

parse-initd() {
  local src=/etc/init.d 
  # NOTE: These scripts don't end with *.sh
  _parse-many \
    $src \
    $RESULT_DIR/initd-parsed \
    $(find $src -type f -a -executable -a -printf '%P\n')
}

parse-debootstrap() {
  local src=~/git/basis-build/_tmp/debootstrap-1.0.48+deb7u2

  # NOTE: These scripts don't end with *.sh
  _parse-many \
    $src \
    $RESULT_DIR/debootstrap-parsed \
    $(find $src '(' -name debootstrap -o -name functions ')' -a -printf '%P\n') \
    $(find $src/scripts -type f -a -printf 'scripts/%P\n')
}

# WOW.  I found another lexical state in Bazel.  How to I handle this?
# Anything that's not a space?  Yeah I think after
# () is allowed as a literal
# [[ "${COMMANDS}" =~ ^$keywords(,$keywords)*$ ]] || usage "$@"

parse-git-other() {
  local src=~/git/other
  local depth=3
  _parse-many \
    $src \
    $RESULT_DIR/git-other-parsed \
    $(find $src -maxdepth $depth -name '*.sh' -a -printf '%P\n')
}

parse-hg-other() {
  local src=~/hg/other
  _parse-many \
    $src \
    $RESULT_DIR/hg-other-parsed \
    $(find $src -name '*.sh' -a -printf '%P\n')
}

parse-git() {
  _parse-project ~/git/other/git
}

parse-dokku() {
  local src=~/git/other/dokku

  time _parse-many \
    $src \
    $RESULT_DIR/dokku-parsed \
    $(find $src '(' -name '*.sh' -o -name dokku ')' -a -printf '%P\n')
}

parse-mesos() {
  _parse-project ~/git/other/mesos
}

parse-balls() {
  local src=~/git/other/balls

  time _parse-many \
    $src \
    $RESULT_DIR/balls-parsed \
    $(find $src '(' -name '*.sh' -o -name balls -o -name esh ')' -a \
                -printf '%P\n')
}

parse-wwwoosh() {
  _parse-project ~/git/other/wwwoosh
}

parse-make-a-lisp() {
  local src=~/git/other/mal/bash

  time _parse-many \
    $src \
    $RESULT_DIR/make-a-lisp-parsed \
    $(find $src '(' -name '*.sh' ')' -a -printf '%P\n')
}

parse-gherkin() {
  local src=~/git/other/gherkin

  time _parse-many \
    $src \
    $RESULT_DIR/gherkin-parsed \
    $(find $src '(' -name '*.sh' -o -name 'gherkin' ')' -a -printf '%P\n')
}

parse-lishp() {
  _parse-project ~/git/other/lishp
}

parse-bashcached() {
  local src=~/git/other/bashcached

  time _parse-many \
    $src \
    $RESULT_DIR/bashcached-parsed \
    $(find $src '(' -name '*.sh' -o -name 'bashcached' ')' -a -printf '%P\n')
}

parse-quinedb() {
  local src=~/git/other/quinedb

  time _parse-many \
    $src \
    $RESULT_DIR/quinedb-parsed \
    $(find $src '(' -name '*.sh' -o -name 'quinedb' ')' -a -printf '%P\n')
}

parse-bashttpd() {
  local src=~/git/other/bashttpd

  time _parse-many \
    $src \
    $RESULT_DIR/bashttpd \
    $(find $src -name 'bashttpd' -a -printf '%P\n')
}

parse-chef-bcpc() {
  _parse-project ~/git/other/chef-bcpc
}

parse-julia() {
  _parse-project ~/git/other/julia
}

# uses a bare "for" in a function!
parse-j() {
  local src=~/git/other/j

  time _parse-many \
    $src \
    $RESULT_DIR/j-parsed \
    $(find $src -type f -a  -name j -a -printf '%P\n')
}

parse-json-sh() {
  _parse-project ~/git/other/JSON.sh
}

# declare -a foo=(..) is not parsed right
parse-shasm() {
  _parse-project ~/git/scratch/shasm
}

parse-sandstorm() {
  _parse-project ~/git/other/sandstorm
}

parse-kubernetes() {
  _parse-project ~/git/other/kubernetes
}

parse-sdk() {
  _parse-project ~/git/other/sdk
}

# korn shell stuff
parse-ast() {
  _parse-project ~/git/other/ast
}

parse-bazel() {
  _parse-project ~/git/other/bazel
}

parse-bash-completion() {
  local src=~/git/other/bash-completion

  time _parse-many \
    $src \
    $RESULT_DIR/bash-completion-parsed \
    $(find $src/completions -type f -a -printf 'completions/%P\n')
}

parse-protobuf() {
  _parse-project ~/git/other/protobuf
}

parse-mksh() {
  _parse-project ~/src/mksh
}

parse-exp() {
  _parse-project ~/git/other/exp
}

parse-minimal-linux() {
  _parse-project ~/git/other/minimal
}

#
# Big projects
#

parse-linux() {
  _parse-project ~/src/linux-4.8.7
}

parse-mozilla() {
  _parse-project \
    /mnt/ssd-1T/build/ssd-backup/sdb/build/hg/other/mozilla-central/
}

parse-chrome() {
  _parse-project \
    /mnt/ssd-1T/build/ssd-backup/sdb/build/chrome
}

parse-chrome2() {
  _parse-configure-scripts \
    /mnt/ssd-1T/build/ssd-backup/sdb/build/chrome
}

parse-android() {
  _parse-project \
    /mnt/ssd-1T/build/ssd-backup/sdb/build/android
}

parse-android2() {
  _parse-configure-scripts \
    /mnt/ssd-1T/build/ssd-backup/sdb/build/android
}

parse-openwrt() {
  _parse-project \
    /mnt/ssd-1T/build/ssd-backup/sdb/build/openwrt
}

parse-openwireless() {
  _parse-project \
    /mnt/ssd-1T/build/ssd-backup/sdb/build/OpenWireless
}

"$@"

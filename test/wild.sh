#!/bin/bash
#
# Run the osh parser on shell scripts found in the wild.
#
# Usage:
#   ./wild.sh <function name>
#
# TODO:
# - There are a lot of hard-coded source paths here.  These files could
# published in a tarball or torrent.
#
# - Need to create an overview HTML page
# - Need to create an index page
#   - original source.

set -o nounset
set -o pipefail
set -o errexit

readonly RESULT_DIR=_tmp/wild

#
# Helpers
# 

log() {
  echo "$@" 1>&2
}

# Default abbrev-text format
osh-parse() {
  bin/osh --ast-output - --no-exec "$@"
}

# TODO: err file always exists because of --no-exec
_parse-one() {
  local input=$1
  local output=$2

  local stderr_file=${output}__err.txt
  osh-parse $input > $output-AST.txt 2> $stderr_file
  local status=$?

  return $status
}

osh-html() {
  bin/osh --ast-output - --ast-format abbrev-html --no-exec "$@"
}

_osh-html-one() {
  local input=$1
  local output=$2

  local stderr_file=${output}__htmlerr.txt
  osh-html $input > $output-AST.html 2> $stderr_file
  local status=$?

  return $status
}

osh-to-oil() {
  bin/osh --no-exec --fix "$@"
}

_osh-to-oil-one() {
  local input=$1
  local output=$2

  local stderr_file=${output}__osh-to-oil-err.txt
  # NOTE: Need text extension for some web servers.
  osh-to-oil $input > ${output}.oil.txt 2> $stderr_file
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
  echo $input

  # Add .txt extension so it's not executable, and use 'cat' instead of cp
  # So it's not executable.
  cat < $input > ${output}.txt

  if ! _parse-one $input $output; then  # Conver to text AST
    echo $rel_path >>$dest_base/FAILED.txt

    # Append
    cat >>$dest_base/FAILED.html <<EOF
    <a href="$rel_path.txt">$rel_path.txt</a>
    <a href="${rel_path}__err.txt">${rel_path}__err.txt</a>
    <a href="$rel_path-AST.txt">$rel_path-AST.txt</a>
    <br/>
    <pre>
    $(cat ${output}__err.txt)
    </pre>
    <hr/>
EOF

    log "*** Failed to parse $rel_path"
    return 1
  fi
  #rm ${output}__err.txt

  if ! _osh-html-one $input $output; then  # Convert to HTML AST
    return 1
  fi

  if ! _osh-to-oil-one $input $output; then  # Convert to Oil
    return 1
  fi
}

_link-or-copy() {
  # Problem: Firefox treats symlinks as redirects, which breaks the AJAX.  Copy
  # it for now.
  local src=$1
  local dest=$2
  #ln -s -f --verbose ../../../$src $dest
  cp -f --verbose $src $dest
}

_parse-many() {
  local src_base=$1
  local dest_base=$2
  shift 2
  # Rest of args are relative paths

  mkdir -p $dest_base

  { pushd $src_base >/dev/null
    wc -l "$@"
    popd >/dev/null
  } > $dest_base/LINE-COUNTS.txt

  # Don't call it index.html
  make-index < $dest_base/LINE-COUNTS.txt > $dest_base/FILES.html

  _link-or-copy web/osh-to-oil.html $dest_base
  _link-or-copy web/osh-to-oil.js $dest_base
  _link-or-copy web/osh-to-oil-index.css $dest_base

  # Truncate files
  echo -n '' >$dest_base/FAILED.txt
  echo -n '' >$dest_base/FAILED.html

  for f in "$@"; do echo $f; done |
    sort |
    xargs -n 1 -- $0 _parse-and-copy-one $src_base $dest_base

  tree -p $dest_base
}

make-index() {
  cat << EOF
<html>
<head>
  <link rel="stylesheet" type="text/css" href="osh-to-oil-index.css" />
</head>
<body>
<p> <a href="..">Up</a> </p>

<h2>Files in this Project</h2>

<table>
EOF
  echo "<thead> <tr> <td align=right>Count</td> <td>Name</td> </tr> </thead>";
  while read count name; do
    echo -n "<tr> <td align=right>$count</td> "
    if test $name == 'total'; then
      echo -n "<td>$name</td>"
    else
      echo -n "<td><a href=\"osh-to-oil.html#${name}\">$name</a></td> </tr>"
    fi
    echo "</tr>"
  done
  cat << EOF
</table>
</body>
</html>
EOF
}

# generic helper
_parse-project() {
  local src=$1
  local name=$(basename $src)

  time _parse-many \
    $src \
    $RESULT_DIR/$name \
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
    $RESULT_DIR/oil-sketch \
    $(cd $src && echo *.sh {awk,demo,make,misc,regex,tools}/*.sh)
}

this-repo() {
  local src=$PWD
  _parse-many \
    $src \
    $RESULT_DIR/oil \
    configure install *.sh {benchmarks,build,test,scripts,opy}/*.sh
}

readonly ABORIGINAL_DIR=~/src/aboriginal-1.4.5

parse-aboriginal() {
  # We want word splitting
  _parse-many \
    $ABORIGINAL_DIR \
    $RESULT_DIR/aboriginal \
    $(find $ABORIGINAL_DIR -name '*.sh' -printf '%P\n')
}

parse-initd() {
  local src=/etc/init.d 
  # NOTE: These scripts don't end with *.sh
  _parse-many \
    $src \
    $RESULT_DIR/initd \
    $(find $src -type f -a -executable -a -printf '%P\n')
}

parse-pixelb-scripts() {
  local src=~/git/other/pixelb-scripts
  # NOTE: These scripts don't end with *.sh
  _parse-many \
    $src \
    $RESULT_DIR/pixelb-scripts \
    $(find $src \( -name .git -a -prune \) -o \
                \(  -type f -a -executable -a -printf '%P\n' \) )
}

parse-debootstrap() {
  # Version 1.0.89 extracts to a version-less dir.
  local src=~/git/basis-build/_tmp/debootstrap

  # NOTE: These scripts don't end with *.sh
  _parse-many \
    $src \
    $RESULT_DIR/debootstrap \
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
    $RESULT_DIR/dokku \
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

# Doesn't parse because of extended glob.
parse-wd() {
  local src=~/git/other/wd

  time _parse-many \
    $src \
    $RESULT_DIR/wd \
    $(find $src -type f -a  -name wd -a -printf '%P\n')
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

parse-micropython() {
  _parse-project ~/git/other/micropython
}

parse-staticpython() {
  _parse-project ~/git/other/staticpython
}

parse-linuxkit() {
  _parse-project ~/git/other/linuxkit
}

# NOTE:
# Find executable scripts, since they don't end in sh.
# net/tcpretrans is written in Perl.
parse-perf-tools() {
  local src=~/git/other/perf-tools
  local files=$(find $src \
                \( -name .git -a -prune \) -o \
                \( -name tcpretrans -a -prune \) -o \
                \( -type f -a -executable -a -printf '%P\n' \) )
  #echo $files
  time _parse-many \
    $src \
    $RESULT_DIR/perf-tools-parsed \
    $files
}

# Bats bash test framework.  It appears to be fairly popular.
parse-bats() {
  local src=~/git/other/bats
  local files=$(find $src \
                \( -wholename '*/libexec/*' -a -type f -a -executable -a -printf '%P\n' \) )
  time _parse-many \
    $src \
    $RESULT_DIR/bats \
    $files
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

#
# Search Aboriginal Packages
#

readonly AB_PACKAGES=~/hg/scratch/aboriginal/aboriginal-1.2.2/packages

aboriginal-packages() {
  for z in $AB_PACKAGES/*.tar.gz; do
    local name=$(basename $z .tar.gz)
    echo $z -z $name
  done
  for z in $AB_PACKAGES/*.tar.bz2; do
    local name=$(basename $z .tar.bz2)
    echo $z -j $name
  done
}

readonly AB_OUT=_tmp/aboriginal

aboriginal-manifest() {
  mkdir -p $AB_OUT

  aboriginal-packages | while read z tar_flag name; do
    echo $z $name
    local listing=$AB_OUT/${name}.txt
    tar --list --verbose $tar_flag < $z | grep '\.sh$' > $listing || true
  done
}

aboriginal-biggest() {
  # print size and filename
  cat $AB_OUT/*.txt | awk '{print $3 " " $6}' | sort -n
}

# biggest scripts besides ltmain:
#
# 8406 binutils-397a64b3/binutils/embedspu.sh
# 8597 binutils-397a64b3/ld/emulparams/msp430all.sh
# 9951 bash-2.05b/examples/scripts/dd-ex.sh
# 12558 binutils-397a64b3/ld/genscripts.sh
# 14148 bash-2.05b/examples/scripts/adventure.sh
# 21811 binutils-397a64b3/gas/testsuite/gas/xstormy16/allinsn.sh
# 28004 bash-2.05b/examples/scripts/bcsh.sh
# 29666 gcc-4.2.1/ltcf-gcj.sh
# 33972 gcc-4.2.1/ltcf-c.sh
# 39048 gcc-4.2.1/ltcf-cxx.sh

"$@"

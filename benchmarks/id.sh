#!/usr/bin/env bash
#
# Keep track of benchmark data provenance.
#
# Usage:
#   benchmarks/id.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)

source build/common.sh  # for $CLANG
source benchmarks/common.sh
source test/tsv-lib.sh  # tsv-row

print-job-id() {
  date '+%Y-%m-%d__%H-%M-%S'
}

# TODO: add benchmark labels/hashes for osh and all other shells
#
# Need to archive labels too.
#
# TODO: How do I make sure the zsh label is current?  Across different
# machines?
#
# What happens when zsh is silently upgraded?
# I guess before every benchmark, you have to run the ID collection.  Man
# that is a lot of code.
#
# Should I make symlinks to the published location?
#
# Maybe bash/dash/mksh/zsh should be invoked through a symlink?
# Every symlink is a shell runtime version, and it has an associated
# toolchain?

# Platform is ambient?
# _tmp/
#   shell-id/
#     bash/
#       HASH.txt
#       version.txt
#     dash/
#       HASH.txt
#       version.txt
#   host-id/
#     lisa/
#       HASH.txt
#       cpuinfo.txt

# ../benchmark-data/
#   shell-id/
#     bash-$HASH/
#     osh-$HASH/   # osh-cpython, osh-ovm?   osh-opy-ovm?  Too many dimensions.
#                # the other shells don't have this?
#     zsh-$HASH/
#   host-id/
#     lisa-$HASH/

_dump-if-exists() {
  local path=$1
  local out=$2
  if ! test -f "$path"; then
    return
  fi
  cat "$path" > $out
}

#
# Shell ID
#

dump-shell-id() {
  ### Write files that identify the shell

  local sh_path=$1
  local out_dir=$2

  if ! command -v $sh_path >/dev/null; then
    die "dump-shell-id: Couldn't find $sh_path"
  fi

  mkdir -p $out_dir

  echo $sh_path > $out_dir/sh-path.txt

  # Add extra repository info for osh.
  case $sh_path in
    */osh*|*/ysh*)
      local commit_hash=$out_dir/git-commit-hash.txt

      if test -n "${XSHAR_GIT_COMMIT:-}"; then
        echo "$XSHAR_GIT_COMMIT" > $commit_hash
      else
        local branch
        branch=$(git rev-parse --abbrev-ref HEAD)
        echo $branch > $out_dir/git-branch.txt
        git rev-parse $branch > $commit_hash
      fi
      ;;
  esac

  local sh_name
  sh_name=$(basename $sh_path)

  case $sh_name in
    bash|zsh|yash)
      $sh_path --version > $out_dir/version.txt
      ;;
    osh)
      case $sh_path in
        *_bin/*/osh)  # Is this branch dead?
          # Doesn't support --version yet
          ;;
        *)
          $sh_path --version > $out_dir/osh-version.txt
          ;;
      esac
      ;;
    ysh)
      $sh_path --version > $out_dir/ysh-version.txt
      ;;
    awk)
      $sh_path --version > $out_dir/awk-version.txt
      ;;

    # oils-for-unix|oils-for-unix.stripped)
    #  ;;
    dash|mksh)
      # These don't have version strings!
      dpkg -s $sh_name > $out_dir/dpkg-version.txt
      ;;

    # not a shell, but useful for benchmarks/compute
    python2)
      $sh_path -V 2> $out_dir/version.txt
      ;;
    *)
      die "Invalid shell '$sh_name'"
      ;;
  esac
}

_shell-id-hash() {
  local src=$1

  local file

  # for shells and Python
  file=$src/version.txt
  test -f $file && cat $file

  # Only hash the dimensions we want to keep
  file=$src/dpkg-version.txt
  test -f $file && egrep '^Version' $file

  # Interpreter as CPython vs. OVM is what we care about, so
  # select 'Interpreter:' but not 'Interpreter version:'.
  # For example, the version is different on Ubuntu Bionic vs. Trusty, but we
  # ignore that.
  file=$src/osh-version.txt
  test -f $file && egrep '^Oil version|^Interpreter:' $file

  # For OSH
  file=$src/git-commit-hash.txt
  test -f $file && cat $file
  # XXX: Include shell path to help distinguish between versions of OSH
  echo $src

  return 0
}

publish-shell-id() {
  ### Copy temp directory to hashed location

  local src=$1  # e.g. _tmp/prov-tmp/osh
  local dest_base=${2:-../benchmark-data/shell-id}  # or _tmp/shell-id

  local sh_path sh_name
  read sh_path < $src/sh-path.txt
  sh_name=$(basename $sh_path)

  local hash
  hash=$(_shell-id-hash $src | md5sum)  # not secure, an identifier

  local id="${hash:0:8}"
  local dest="$dest_base/$sh_name-$id"

  mkdir -p $dest
  cp --no-target-directory --recursive $src/ $dest/

  echo $hash > $dest/HASH.txt

  log "Published shell ID to $dest"

  echo $id
}

#
# Platform ID
#

# Events that will change the env for a given machine:
# - kernel upgrade
# - distro upgrade

# How about ~/git/oilshell/benchmark-data/host-id/lisa-$HASH
# How to calculate the hash though?

dump-host-id() {
  ### Write files that identify the host

  local out_dir=${1:-_tmp/host-id/$(hostname)}

  mkdir -p $out_dir

  hostname > $out_dir/hostname.txt

  # does it make sense to do individual fields like -m?
  # avoid parsing?
  # We care about the kernel and the CPU architecture.
  # There is a lot of redundant information there.
  uname -m > $out_dir/machine.txt

  {
    # Short flags work on OS X too
    uname -s  # --kernel-name
    uname -r  # --kernel-release
    uname -v  # --kernel-version
  } > $out_dir/kernel.txt

  _dump-if-exists /etc/lsb-release $out_dir/lsb-release.txt

  # remove the cpu MHz field, which changes a lot
  if test -e /proc/cpuinfo; then
    grep -i -v 'cpu mhz' /proc/cpuinfo > $out_dir/cpuinfo.txt
  fi

  # mem info doesn't make a difference?  I guess it's just nice to check that
  # it's not swapping.  But shouldn't be part of the hash.

  if test -e /proc/meminfo; then
    grep '^MemTotal' /proc/meminfo > $out_dir/meminfo.txt
  fi

  #head $out_dir/* 1>&2  # don't write to stdout
}

# There is already concept of the triple?
# http://wiki.osdev.org/Target_Triplet
# It's not exactly the same as what we need here, but close.

_host-id-hash() {
  local src=$1

  # Don't hash CPU or memory
  #cat $src/cpuinfo.txt
  #cat $src/hostname.txt  # e.g. lisa

  cat $src/machine.txt  # e.g. x86_64 
  cat $src/kernel.txt

  # OS
  local file=$src/lsb-release.txt
  if test -f $file; then
    cat $file
  fi

  return 0
}

# Writes a short ID to stdout.
publish-host-id() {
  local src=$1  # e.g. _tmp/host-id/lisa
  local dest_base=${2:-../benchmark-data/host-id}

  local name
  name=$(basename $src)

  local hash
  hash=$(_host-id-hash $src | md5sum)  # not secure, an identifier

  local id="${hash:0:8}"
  local dest="$dest_base/$name-$id"

  mkdir -p $dest
  cp --no-target-directory --recursive $src/ $dest/

  echo $hash > $dest/HASH.txt

  log "Published host ID to $dest"

  echo $id
}

#
# Compilers
# 

dump-compiler-id() {
  ### Write files that identify the compiler

  local cc=$1  # path to the compiler
  local out_dir=${2:-_tmp/compiler-id/$(basename $cc)}

  mkdir -p $out_dir

  case $cc in
    */gcc)
      $cc --version
      # -v has more details, but they might be overkill.
      ;;
    */clang)
      $cc --version
      # -v has stuff we don't want
      ;;
  esac > $out_dir/version.txt
}

_compiler-id-hash() {
  local src=$1

  # Remove some extraneous information from clang.
  cat $src/version.txt | grep -v InstalledDir 
}

# Writes a short ID to stdout.
publish-compiler-id() {
  local src=$1  # e.g. _tmp/compiler-id/clang
  local dest_base=${2:-../benchmark-data/compiler-id}

  local name=$(basename $src)
  local hash
  hash=$(_compiler-id-hash $src | md5sum)  # not secure, an identifier

  local id="${hash:0:8}"
  local dest="$dest_base/$name-$id"

  mkdir -p $dest
  cp --no-target-directory --recursive $src/ $dest/

  echo $hash > $dest/HASH.txt

  log "Published compiler ID to $dest"

  echo $id
}

#
# Table Output
#

# Writes a table of host and shells to stdout.  Writes text files and
# calculates IDs for them as a side effect.
#
# The table can be passed to other benchmarks to ensure that their provenance
# is recorded.

shell-provenance-2() {
  ### Write to _tmp/provenance.{txt,tsv} and $out_dir/{shell-id,host-id}

  local maybe_host=$1  # if it exists, it overrides the host
  local job_id=$2
  local out_dir=$3
  shift 3

  # log "*** shell-provenance"

  local host_name
  if test -n "$maybe_host"; then  # label is often 'no-host'
    host_name=$maybe_host
  else
    host_name=$(hostname)
  fi

  log "*** shell-provenance-2 $maybe_host $host_name $job_id $out_dir"

  local tmp_dir=_tmp/prov-tmp/$host_name
  dump-host-id $tmp_dir

  local host_hash
  host_hash=$(publish-host-id $tmp_dir "$out_dir/host-id")

  local shell_hash

  local out_txt=_tmp/provenance.txt  # Legacy text file
  echo -n '' > $out_txt  # truncated, no header

  local out_tsv=_tmp/provenance.tsv
  tsv-row job_id host_name host_hash sh_path shell_hash > $out_tsv

  local i=0

  for sh_path in "$@"; do
    # There can be two different OSH

    tmp_dir=_tmp/prov-tmp/shell-$i
    i=$((i + 1))

    dump-shell-id $sh_path $tmp_dir

    # writes to ../benchmark-data or _tmp/provenance
    shell_hash=$(publish-shell-id $tmp_dir "$out_dir/shell-id")

    # note: filter-provenance depends on $4 being $sh_path
    # APPEND to txt
    echo "$job_id $host_name $host_hash $sh_path $shell_hash" >> $out_txt

    tsv-row "$job_id" "$host_name" "$host_hash" "$sh_path" "$shell_hash" >> $out_tsv
  done

  log "Wrote $out_txt and $out_tsv"
}

provenance-for-testing() { 
  ### For running benchmarks locally

  local out_dir=_tmp/local-benchmarks
  mkdir -v -p $out_dir
  shell-provenance-2 \
    $(hostname) 2025__test-job $out_dir \
    "${SHELLS[@]}" $OSH_CPP_BENCHMARK_DATA python2
}

compiler-provenance-2() {
  # Write to _tmp/compiler-provenance.txt and $out_dir/{compiler-id,host-id}

  local maybe_host=$1  # if it exists, it overrides the host
  local job_id=$2
  local out_dir=$3

  local host_name
  if test -n "$maybe_host"; then  # label is often 'no-host'
    host_name=$maybe_host
  else
    host_name=$(hostname)
  fi

  log "*** compiler-provenance-2 $maybe_host $host_name $job_id $out_dir"

  local tmp_dir=_tmp/prov-tmp/$host_name
  dump-host-id $tmp_dir

  local host_hash
  host_hash=$(publish-host-id $tmp_dir "$out_dir/host-id")

  local compiler_hash

  local out_txt=_tmp/compiler-provenance.txt  # Legacy text file
  echo -n '' > $out_txt  # truncated, no header

  local out_tsv=_tmp/compiler-provenance.tsv
  tsv-row job_id host_name host_hash compiler_path compiler_hash > $out_tsv

  for compiler_path in $(which gcc) $CLANG; do
    local name=$(basename $compiler_path)

    tmp_dir=_tmp/prov-tmp/$name
    dump-compiler-id $compiler_path $tmp_dir

    compiler_hash=$(publish-compiler-id $tmp_dir "$out_dir/compiler-id")

    echo "$job_id $host_name $host_hash $compiler_path $compiler_hash" \
      >> $out_txt

    tsv-row \
      "$job_id" "$host_name" "$host_hash" "$compiler_path" "$compiler_hash" \
      >> $out_tsv
  done

  log "Wrote $out_txt and $out_tsv"
}

out-param() {
  declare -n out=$1

  out=returned
}

if test $(basename $0) = 'id.sh'; then
  "$@"
fi


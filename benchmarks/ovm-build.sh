#!/bin/bash
#
# Measure the time it takes to build a binary, and the size of the binary.
#
# Usage:
#   ./ovm-build.sh <function name>

# Directories used:
#
# _tmp/
#   ovm-build/  
#     raw/     # output CSV
#     stage1
# _deps/
#   ovm-build  # tarballs and extracted source

set -o nounset
set -o pipefail
set -o errexit

source benchmarks/common.sh  # for log, etc.
source build/common.sh  # for $CLANG

readonly BASE_DIR=_tmp/ovm-build
readonly TAR_DIR=$PWD/_deps/ovm-build # Make it absolute

#
# Dependencies
#

readonly OIL_VERSION=$(head -n 1 oil-version.txt)

# Leave out mksh for now, because it doesn't follow ./configure make.  It just
# has Build.sh.
readonly -a TAR_SUBDIRS=( bash-4.4 dash-0.5.9.1 )  # mksh )

# NOTE: Same list in oilshell.org/blob/run.sh.
tarballs() {
  cat <<EOF
bash-4.4.tar.gz
dash-0.5.9.1.tar.gz
mksh-R56c.tgz
EOF
}

download() {
  mkdir -p $TAR_DIR
  tarballs | xargs -n 1 -I {} --verbose -- \
    wget --directory $TAR_DIR 'https://www.oilshell.org/blob/ovm-build/{}'
}

extract-other() {
  time for f in $TAR_DIR/*gz; do
    tar -x --directory $TAR_DIR --file $f 
  done
  ls -l $TAR_DIR
}

extract-oil() {
  local target=_release/oil.tar
  rm -f -v $target
  make $target
  tar -x --directory $TAR_DIR --file $target
  ls -l $TAR_DIR
}

# NOTE: build/test.sh measures the time already.

# Coarse Size and Time Benchmarks
# --------------------------------
# 
# RUN:
#   compiler: CC=gcc or CC=clang
#   host: lisa or flanders
#   target: oil.ovm vs. oil.ovm-dbg
#   Then do benchmarks/time.py of "make CC=$CC"
# 
# Measure:
#   bytecode.zip size vs. ovm size
#   (Forget about individual files for now)
#   end-to-end build time in seconds
# 
# After optimization:
#   ovm should be a lot smaller
#   build time should be lower, as long as you did the #if 0
# 
# LATER:
#   reduce the amount of code.
#   do more fine-grained coverage?  I don't think you necessarily need it to
# reduce code.  You can do it by COMPILE TIME slicing, not runtime! 
# 
# I think doing it function-by-function at compile time is easier.  I need to
# modify Opy to spit out all references though?
#
# Other tools:
# - bloaty to look inside elf file
# - zipfile.py to look inside bytecode.zip

bytecode-size() {
  local zip=_build/oil/bytecode.zip

  # 242 files, 1.85 MB
  unzip -l $zip | tail -n 1 

  # 1.88 MB, so there's 30K of header overhead.
  ls -l $zip
}

# NOTE: ovm-dbg is not stripped, so it's not super meaningful.
binary-size() {
  make _build/oil/ovm{,-dbg}
  ls -l _build/oil/ovm{,-dbg}
}

# 6.8 seconds for debug build, instead of 8 seconds.
clang-oil-dbg() {
  make clean
  CC=$CLANG make _build/oil/ovm-dbg
}

# Add --target-size?  Add that functionality to benchmarks/time.py?
#
# Should we add explicit targets?
#   - ovm-clang, ovm-clang-dbg
#   - ovm-gcc, ovm-gcc-dbg
#
# It would be possible, but it complicates the makefile.

build-task() {
  local raw_dir=$1  # output
  local job_id=$2
  local host=$3
  local host_hash=$4
  local compiler_path=$5
  local compiler_hash=$6
  local src_dir=$7
  local action=$8

  local times_out="$PWD/$raw_dir/$host.$job_id.times.csv"

  local -a TIME_PREFIX=(
    $PWD/benchmarks/time.py \
    --output $times_out \
    --field "$host" --field "$host_hash" \
    --field "$compiler_path" --field "$compiler_hash" \
    --field "$src_dir" --field "$action"
  )

  pushd $src_dir >/dev/null

  # NOTE: We're not saving the output anywhere.  We save the status, which
  # protects against basic errors.

  case $action in
    configure)
      # Cleaning here relies on the ORDER of tasks.txt.  configure happens
      # before build.  The Clang build shouldn't reuse GCC objects!
      make clean
      "${TIME_PREFIX[@]}" -- ./configure
      ;;
    make)
      "${TIME_PREFIX[@]}" -- make CC=$compiler_path
      ;;
    *)
      # Assume it's a target.
      "${TIME_PREFIX[@]}" -- make CC=$compiler_path $action
      ;;
  esac

  popd >/dev/null
}

oil-tasks() {
  local provenance=$1

  # NOTE: it MUST be a tarball and not the git repo, because we do the build
  # of bytecode.zip!  We care about the "package experience".
  local dir="$TAR_DIR/oil-$OIL_VERSION"

  # Add 1 field for each of 5 fields.
  cat $provenance | while read line; do
    # NOTE: configure is independent of compiler.
    echo "$line" $dir configure
    echo "$line" $dir _bin/oil.ovm
    echo "$line" $dir _bin/oil.ovm-dbg
  done
}

other-shell-tasks() {
  local provenance=$1

  # NOTE: it MUST be a tarball and not the git repo, because we do the build
  # of bytecode.zip!  We care about the "package experience".
  local tarball='_release/oil.0.5.alpha1.gz'

  # Add 1 field for each of 5 fields.
  cat $provenance | while read line; do
    case $line in
      # Skip clang for now.
      *clang*)
        continue
        ;;
    esac

    for dir in "${TAR_SUBDIRS[@]}"; do
      echo "$line" $TAR_DIR/$dir configure
      echo "$line" $TAR_DIR/$dir make
    done
  done
}

# 5 releases: 0.0.0 to 0.4.0.  For now, just do the 0.5.alpha1 release, and
# show the drop.
oil-historical-tasks() {
  echo 
}

# action is 'configure', a target name, etc.
readonly HEADER='status,elapsed_secs,host_name,host_hash,compiler_path,compiler_hash,src_dir,action'
readonly NUM_COLUMNS=7  # 5 from provenence, then tarball/target

measure() {
  local provenance=$1  # from benchmarks/id.sh compiler-provenance
  local raw_dir=${2:-$BASE_DIR/raw}

  #local base_dir=${2:-../benchmark-data/osh-parser}

  # Job ID is everything up to the first dot in the filename.
  local name=$(basename $provenance)
  local prefix=${name%.compiler-provenance.txt}  # strip suffix

  local times_out="$raw_dir/$prefix.times.csv"
  mkdir -p $BASE_DIR/{raw,stage1}

  # TODO: the $times_out calculation is duplicated in build-task()0

  # Write Header of the CSV file that is appended to.
  echo $HEADER > $times_out

  local t1=$BASE_DIR/oil-tasks.txt
  local t2=$BASE_DIR/other-shell-tasks.txt

  oil-tasks $provenance > $t1
  other-shell-tasks $provenance > $t2

  time cat $t1 $t2 |
    xargs -n $NUM_COLUMNS -- $0 build-task $raw_dir ||
    die "*** Some tasks failed. ***"

  cp -v $provenance $raw_dir
}

"$@"

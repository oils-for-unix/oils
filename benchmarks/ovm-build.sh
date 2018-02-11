#!/bin/bash
#
# Measure the time it takes to build a binary, and the size of the binary.
#
# Usage:
#   ./ovm-build.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source build/common.sh  # for $CLANG

readonly BASE_DIR=_tmp/ovm-build

# NOTE: build/test.sh measures the time already.

# Coarse Size and Time Benchmarks
# --------------------------------
# 
# RUN:
#   compiler: CC=gcc or CC=clang
#   host: lisa or flanders
#   target: oil.ovm vs. oil.ovm-dbg
#   Then do benchmarks/time.py of "make CC=$CC"
#   make clean between?
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
clang() {
  make clean
  CC=$CLANG make _build/oil/ovm-dbg
}

# TODO: Follow pattern in benchmarks/osh-{runtime,parser} ?
# You get provenance.txt, and
# But that is measuring against bash and dash BINARIES.  At the very least, we
# want to measure bash, dash, mksh compile times.

# target is _build/oil/ovm
#
# So we need another provenance function.  Instead of host/shell name/hash, we
# need host/compiler name/hash.

# Add --target-size?  Add that functionality to benchmarks/time.py?
#
# Should we add explicit targets?
#   - ovm-clang, ovm-clang-dbg
#   - ovm-gcc, ovm-gcc-dbg
#
# It would be possible, but it complicates the makefile.

#readonly HEADER='status,elapsed_secs,host_name,host_hash,compiler_name,compiler_hash,tarball,target,target_num_bytes'

# 5 releases: 0.0.0 to 0.4.0.  Or we could just do the 0.5.alpha1 release?
# Then you can show the drop.
oil-historical() {
  echo 
}

# maybe just ./configure and compile each shell with GCC?  Just for a ballpark
# comparison.  It doesn't have to get too detailed.
# Put it in benchmark-data/saved ?
# Multiple hosts are useful though.  I may change hosts.  I might want to run
# it again on Clang upgrades?  As a control?

other-shells() {
  echo
}

build-task() {
  local raw_dir=$1  # output
  local job_id=$2
  local host=$3
  local host_hash=$4
  local compiler_path=$5
  local compiler_hash=$6
  local tarball=$7
  local target=$8

  # Really we should just measure "make", and then the ovm-dbg target can be
  # separate?
  # We also want to do ./configure.  Do that for bash/dash too.

  # time them with benchmarks/time.py
  echo TODO $tarball $target
}

print-tasks() {
  local provenance=$1

  # NOTE: it MUST be a tarball and not the git repo, because we do the build
  # of bytecode.zip!  We care about the "package experience".
  local tarball='_release/oil.0.5.alpha1.gz'

  # Add 1 field for each of 5 fields.
  cat $provenance | while read line; do
    echo "$line" $tarball _build/oil/ovm
    echo "$line" $tarball _build/oil/ovm-dbg
  done
}


readonly HEADER='status,elapsed_secs,host_name,host_hash,compiler_path,compiler_hash,tarball,target'
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

  # Write Header of the CSV file that is appended to.
  echo $HEADER > $times_out

  local tasks=$BASE_DIR/tasks.txt
  print-tasks $provenance > $tasks

  time cat $tasks |
    xargs -n $NUM_COLUMNS -- $0 build-task $raw_dir ||
    die "*** Some tasks failed. ***"

  cp -v $provenance $raw_dir
}

"$@"

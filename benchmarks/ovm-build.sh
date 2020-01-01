#!/bin/bash
#
# Measure the time it takes to build a binary with different compilers on
# different machines, and measure the binary size.
#
# Usage:
#   ./ovm-build.sh <function name>

# Directories used:
#
# oilshell.org/blob/
#  ovm-build/
#
# ~/git/oilshell/
#   oil/
#     _deps/
#       ovm-build  # tarballs and extracted source
#     _tmp/
#       ovm-build/  
#         raw/     # output CSV
#         stage1
#   benchmark-data/
#     ovm-build/
#       raw/
#     compiler-id/
#     host-id/

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

# Done MANUALLY.
extract-other() {
  time for f in $TAR_DIR/*gz; do
    tar -x --directory $TAR_DIR --file $f 
  done
}

# Done automatically by 'measure' function.
#
# NOTE: We assume that _release/oil.tar exists.  It should be made by
# scripts/release.sh build-and-test or benchmark-build.
extract-oil() {
  # This is different than the others tarballs.
  rm -r -f -v $TAR_DIR/oil-*
  tar -x --directory $TAR_DIR --file _release/oil.tar

  # To run on multiple machines, use the one in the benchmarks-data repo.
  cp --recursive --no-target-directory \
    ../benchmark-data/src/oil-native-$OIL_VERSION/ \
    $TAR_DIR/oil-native-$OIL_VERSION/
}

#
# Measure Size of Binaries.
#

# Other tools:
# - bloaty to look inside elf file
# - nm?  Just a flat list of symbols?  Counting them would be nice.
# - zipfile.py to look inside bytecode.zip

sizes-tsv() {
  # host_label matches the times.tsv file output by report.R
  echo $'host_label\tnum_bytes\tpath'
  local host=$(hostname)
  find "$@" -maxdepth 0 -printf "$host\t%s\t%p\n"
}

# NOTE: This should be the same on all x64 machines.  But I want to run it on
# x64 machines.
measure-sizes() {
  local prefix=${1:-$BASE_DIR/raw/demo}

  # PROBLEM: Do I need provenance for gcc/clang here?  I can just join it later
  # in R.

  sizes-tsv $BASE_DIR/bin/*/osh_parse.{dbg,opt.stripped} \
    > ${prefix}.native-sizes.tsv

  sizes-tsv $TAR_DIR/oil-$OIL_VERSION/_build/oil/bytecode-opy.zip \
    > ${prefix}.bytecode-size.tsv

  sizes-tsv $BASE_DIR/bin/*/oil.* \
    > ${prefix}.bin-sizes.tsv

  sizes-tsv $BASE_DIR/bin/*/*sh \
    > ${prefix}.other-shell-sizes.tsv

  log "Wrote ${prefix}.*.tsv"

  # Native portion, but it's not separated out by compiler.  We can just
  # subtract.
  #$TAR_DIR/oil-$OIL_VERSION/_build/oil/ovm* \
}

#
# Unused Demos
#

bytecode-size() {
  local zip=_build/oil/bytecode.zip

  # 242 files, 1.85 MB
  unzip -l $zip | tail -n 1 

  # 1.88 MB, so there's 30K of header overhead.
  ls -l $zip
}

# 6.8 seconds for debug build, instead of 8 seconds.
clang-oil-dbg() {
  make clean
  CC=$CLANG make _build/oil/ovm-dbg
}

#
# Measure Elapsed Time
#

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

  local times_out="$PWD/$raw_dir/$host.$job_id.times.tsv"

  # Definitions that depends on $PWD.
  local -a TIME_PREFIX=(
    time-tsv \
    --output $times_out \
    --field "$host" --field "$host_hash" \
    --field "$compiler_path" --field "$compiler_hash" \
    --field "$src_dir" --field "$action"
  )
  local bin_base_dir=$PWD/$BASE_DIR/bin
  local bin_dir="$bin_base_dir/$(basename $compiler_path)"
  mkdir -p $bin_dir

  pushd $src_dir >/dev/null

  # NOTE: We're not saving the output anywhere.  We save the status, which
  # protects against basic errors.

  case $action in
    configure)
      "${TIME_PREFIX[@]}" -- ./configure

      # Cleaning here relies on the ORDER of tasks.txt.  configure happens
      # before build.  The Clang build shouldn't reuse GCC objects!
      # It has to be done after configure, because the Makefile must exist!
      make clean
      ;;

    make)
      "${TIME_PREFIX[@]}" -- make CC=$compiler_path

      local target
      case $src_dir in
        */bash*)
          target=bash
          ;;
        */dash*)
          target=src/dash
          ;;
      esac

      strip $target
      cp -v $target $bin_dir
      ;;

    _bin/osh_parse.*)
      case $action in
        _bin/osh_parse.dbg)
          local func='compile-osh-parse'
          ;;
        _bin/osh_parse.opt.stripped)
          local func='compile-osh-parse-opt'
          ;;
        *)
          die "Invalid target"
          ;;
      esac

      # Change the C compiler into the corresponding C++ compiler
      case $compiler_path in 
        *gcc)
          cxx=${compiler_path//gcc/g++}
          ;;
        *clang)
          # clang -> clang++.  There is also a 'clang' in the path so we can't
          # substitute.
          cxx="${compiler_path}++"
          ;;
        *)
          die "Invalid compiler"
          ;;
      esac

      CXX=$cxx "${TIME_PREFIX[@]}" -- build/mycpp.sh $func

      local target=$action
      cp -v $target $bin_dir
      ;;

    *)
      local target=$action  # Assume it's a target like _bin/oil.ovm

      "${TIME_PREFIX[@]}" -- make CC=$compiler_path $target

      cp -v $target $bin_dir
      ;;
  esac

  popd >/dev/null

  log "DONE BUILD TASK $action $src_dir __ status=$?"
}

oil-tasks() {
  local provenance=$1

  # NOTE: it MUST be a tarball and not the git repo, because we don't build
  # bytecode-*.zip!  We care about the "packager's experience".
  local oil_dir="$TAR_DIR/oil-$OIL_VERSION"
  local oil_native_dir="$TAR_DIR/oil-native-$OIL_VERSION"

  # Add 1 field for each of 5 fields.
  cat $provenance | while read line; do
    # NOTE: configure is independent of compiler.
    echo "$line" $oil_dir configure
    echo "$line" $oil_dir _bin/oil.ovm
    echo "$line" $oil_dir _bin/oil.ovm-dbg

    echo "$line" $oil_native_dir _bin/osh_parse.dbg
    echo "$line" $oil_native_dir _bin/osh_parse.opt.stripped
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
readonly HEADER=$'status\telapsed_secs\thost_name\thost_hash\tcompiler_path\tcompiler_hash\tsrc_dir\taction'
readonly NUM_COLUMNS=7  # 5 from provenence, then tarball/target

measure() {
  local provenance=$1  # from benchmarks/id.sh compiler-provenance
  local raw_dir=${2:-$BASE_DIR/raw}

  extract-oil

  # Job ID is everything up to the first dot in the filename.
  local name=$(basename $provenance)
  local prefix=${name%.compiler-provenance.txt}  # strip suffix

  local times_out="$raw_dir/$prefix.times.tsv"
  # NOTE: Do we need two raw dirs?
  mkdir -p $BASE_DIR/{raw,stage1,bin} $raw_dir

  # TODO: the $times_out calculation is duplicated in build-task()0

  # Write Header of the CSV file that is appended to.
  echo "$HEADER" > $times_out

  local t1=$BASE_DIR/oil-tasks.txt
  local t2=$BASE_DIR/other-shell-tasks.txt

  oil-tasks $provenance > $t1
  other-shell-tasks $provenance > $t2

  #grep dash $t2 |
  #time cat $t1 |
  set +o errexit
  time cat $t1 $t2 | xargs --verbose -n $NUM_COLUMNS -- $0 build-task $raw_dir 
  local status=$?
  set -o errexit

  if test $status -ne 0; then
    die "*** Some tasks failed. (xargs status=$status) ***"
  fi

  measure-sizes $raw_dir/$prefix

  cp -v $provenance $raw_dir
}

#
# Data Preparation and Analysis
#

stage1() {
  local raw_dir=${1:-$BASE_DIR/raw}

  local out=$BASE_DIR/stage1
  mkdir -p $out

  local x
  local -a a b

  # Globs are in lexicographical order, which works for our dates.
  x=$out/times.tsv
  a=($raw_dir/$MACHINE1.*.times.tsv)
  b=($raw_dir/$MACHINE2.*.times.tsv)
  tsv-concat ${a[-1]} ${b[-1]} > $x

  x=$out/bytecode-size.tsv
  a=($raw_dir/$MACHINE1.*.bytecode-size.tsv)
  b=($raw_dir/$MACHINE2.*.bytecode-size.tsv)
  tsv-concat ${a[-1]} ${b[-1]} > $x

  x=$out/bin-sizes.tsv
  a=($raw_dir/$MACHINE1.*.bin-sizes.tsv)
  b=($raw_dir/$MACHINE2.*.bin-sizes.tsv)
  tsv-concat ${a[-1]} ${b[-1]} > $x

  x=$out/native-sizes.tsv
  a=($raw_dir/$MACHINE1.*.native-sizes.tsv)
  b=($raw_dir/$MACHINE2.*.native-sizes.tsv)
  #tsv-concat ${b[-1]} > $x
  tsv-concat ${a[-1]} ${b[-1]} > $x

  # NOTE: unused
  # Construct a one-column TSV file
  local raw_data_tsv=$out/raw-data.tsv
  { echo 'path'
    echo ${a[-1]}
    echo ${b[-1]}
  } > $raw_data_tsv

  head $out/*
  wc -l $out/*
}

print-report() {
  local in_dir=$1
  local base_url='../../web'

  benchmark-html-head 'OVM Build Performance'

  cat <<EOF
  <body class="width60">
    <p id="home-link">
      <a href="/">oilshell.org</a>
    </p>
    <h2>OVM Build Performance</h2>

    <h3>Time in Seconds by Host and Compiler</h3>

    <p>We measure the build speed of <code>bash</code> and <code>dash</code>
    for comparison.
    </p>
EOF
  tsv2html --css-class-pattern 'special ^oil' $in_dir/times.tsv

  cat <<EOF
    <h3>Binary Size</h3>

    <p>The oil binary has two portions:
      <ol>
        <li>Architecture-independent <code>bytecode.zip</code></li>
        <li>Architecture- and compiler- dependent native code
            (<code>_build/oil/ovm*</code>)
        </li>
      </ol>
    </p>

EOF
  # Highlight the "default" production build
  tsv2html --css-class-pattern 'special /gcc/oil.ovm$' $in_dir/sizes.tsv

  cat <<EOF
    <h3>Native Binary Size</h3>

EOF
  # Highlight the opt build
  tsv2html --css-class-pattern 'special /gcc/osh_parse.opt.stripped$' $in_dir/native-sizes.tsv

  cat <<EOF

    <h3>Host and Compiler Details</h3>
EOF
  tsv2html $in_dir/hosts.tsv
  tsv2html $in_dir/compilers.tsv

  cat <<EOF
  </body>
</html>
EOF
}

"$@"

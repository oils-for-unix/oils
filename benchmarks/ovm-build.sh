#!/usr/bin/env bash
#
# Measure the time it takes to build a binary with different compilers on
# different machines, and measure the binary size.
#
# Usage:
#   benchmarks/ovm-build.sh <function name>
#
# Run on its own:
#   1. Follow common instructions in benchmarks/osh-parser.sh
#   2. benchmarks/auto.sh measure-builds
#   3. benchmarks/report.sh ovm-build

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
source benchmarks/id.sh  # print-job-id
source build/common.sh  # for $CLANG

REPO_ROOT=$(cd $(dirname $0)/..; pwd)
source test/tsv-lib.sh  # uses REPO_ROOT

readonly BASE_DIR=_tmp/ovm-build
readonly TAR_DIR=$PWD/_deps/ovm-build  # Make it absolute

#
# Dependencies
#

readonly -a TAR_SUBDIRS=( 
  dash-0.5.9.1 
  bash-4.4 
)

# NOTE: Same list in oilshell.org/blob/run.sh.
tarballs() {
  cat <<EOF
bash-4.4.tar.gz
dash-0.5.9.1.tar.gz
EOF
}

download() {
  mkdir -p $TAR_DIR
  tarballs | xargs -n 1 -I {} --verbose -- \
    wget --no-clobber --directory $TAR_DIR 'https://www.oilshell.org/blob/ovm-build/{}'
}

# Done MANUALLY.
extract-other() {
  time for f in $TAR_DIR/*gz; do
    tar -x --directory $TAR_DIR --file $f 
  done
}

# Done automatically by 'measure' function.

# TODO: CI should download this from previous
extract-oils() {
  # To run on multiple machines, use the one in the benchmarks-data repo.
  cp --recursive --no-target-directory \
    ../benchmark-data/src/oils-for-unix-$OIL_VERSION/ \
    $TAR_DIR/oils-for-unix-$OIL_VERSION/
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
  tsv-row host_label num_bytes path
  local host=$(hostname)
  find "$@" -maxdepth 0 -printf "$host\t%s\t%p\n"
}

# NOTE: This should be the same on all x64 machines.  But I want to run it on
# x64 machines.
measure-sizes() {
  local raw_out_dir=$1

  # PROBLEM: Do I need provenance for gcc/clang here?  I can just join it later
  # in R.

  # clang/oils-for-unix
  # clang/oils-for-unix.stripped
  # gcc/oils-for-unix
  # gcc/oils-for-unix.stripped
  sizes-tsv $BASE_DIR/bin/*/{oils-for-unix,oils-for-unix.stripped} \
    > ${raw_out_dir}/native-sizes.tsv

  # Not used - we're not stripping these, etc.
  sizes-tsv $BASE_DIR/bin/*/*sh \
    > ${raw_out_dir}/other-shell-sizes.tsv

  log "Wrote ${raw_out_dir}/*.tsv"
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
  local raw_out_dir=$1
  local job_id=$2
  local host=$3
  local host_hash=$4
  local compiler_path=$5
  local compiler_hash=$6
  local src_dir=$7
  local action=$8

  local times_out="$PWD/$raw_out_dir/times.tsv"

  # Definitions that depends on $PWD.
  local -a TIME_PREFIX=(
    time-tsv \
    --append \
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
    (configure)
      "${TIME_PREFIX[@]}" -- ./configure

      # Cleaning here relies on the ORDER of tasks.txt.  configure happens
      # before build.  The Clang build shouldn't reuse GCC objects!
      # It has to be done after configure, because the Makefile must exist!
      make clean
      ;;

    (make)
      "${TIME_PREFIX[@]}" -- make CC=$compiler_path

      local target
      case $src_dir in
        (*/bash*)
          target=bash
          ;;
        (*/dash*)
          target=src/dash
          ;;
      esac

      strip $target
      cp -v $target $bin_dir
      ;;

    (oils-for-unix*)
      case $action in
        (oils-for-unix)
          local variant='dbg'
          ;;
        (oils-for-unix.stripped)
          local variant='opt'
          ;;
        *)
          die "Invalid target"
          ;;
      esac

      # Change the C compiler into the corresponding C++ compiler
      local compiler
      case $compiler_path in 
        (*gcc)
          # note: we take provenance of /usr/bin/gcc, but the shell script runs 'c++'
          compiler='cxx'
          ;;
        (*clang)
          # Note on slight mess: benchmarks/id.sh takes the provenance of
          # $CLANG.  We translate that to 'clang' here, and
          # _build/oils.sh uses $CLANGXX.
          compiler='clang'
          ;;
        *)
          die "Invalid compiler"
          ;;
      esac

      "${TIME_PREFIX[@]}" -- _build/oils.sh --cxx $compiler --variant $variant

      # e.g. cp _bin/clang-opt-sh/oils-for-unix.stripped _tmp/ovm-build/bin/clang/
      local filename=$action
      cp -v _bin/$compiler-$variant-sh/$filename $bin_dir
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

oils-tasks() {
  local provenance=$1

  local ofu_dir="$TAR_DIR/oils-for-unix-$OIL_VERSION"

  # Add 1 field for each of 5 fields.
  cat $provenance | while read line; do
    echo "$line" $ofu_dir oils-for-unix
    echo "$line" $ofu_dir oils-for-unix.stripped
  done
}

other-shell-tasks() {
  local provenance=$1

  # Add 1 field for each of 5 fields.
  cat $provenance | while read line; do
    case $line in
      # Skip clang for now.
      (*clang*)
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
readonly NUM_COLUMNS=7  # 5 from provenence, then tarball/target

print-tasks() {
  local build_prov=$1

  local t1=$BASE_DIR/oils-tasks.txt
  local t2=$BASE_DIR/other-shell-tasks.txt

  oils-tasks $build_prov > $t1
  other-shell-tasks $build_prov > $t2

  if test -n "${QUICKLY:-}"; then
    head -n 2 $t1  # debug and opt binary
    head -n 2 $t2  # do dash configure make
  else
    cat $t1 $t2
  fi
}

measure() {
  local build_prov=$1  # from benchmarks/id.sh compiler-provenance
  local raw_out_dir=$2  # _tmp/ovm-build/$X or ../../benchmark-data/ovm-build/$X

  extract-oils

  local times_out="$raw_out_dir/times.tsv"
  # NOTE: Do we need two raw dirs?
  mkdir -p $BASE_DIR/{stage1,bin} $raw_out_dir

  # TODO: the $times_out calculation is duplicated in build-task()

  # Write header of the TSV file that is appended to.
  tsv-row \
    status elapsed_secs \
    host_name host_hash compiler_path compiler_hash \
    src_dir action > $times_out

  # TODO: remove xargs
  # - print-tasks | run-tasks with a loop
  # - exit code is more reliable, and we're not running in parallel anyway

  set +o errexit
  time print-tasks $build_prov \
    | xargs --verbose -n $NUM_COLUMNS -- $0 build-task $raw_out_dir 
  local status=$?
  set -o errexit

  if test $status -ne 0; then
    die "*** Some tasks failed. (xargs status=$status) ***"
  fi

  measure-sizes $raw_out_dir
}

#
# Data Preparation and Analysis
#

stage1() {
  local base_dir=${1:-$BASE_DIR}  # _tmp/ovm-build or ../benchmark-data/ovm-build
  local single_machine=${2:-}

  local out_dir=$BASE_DIR/stage1
  mkdir -p $out_dir

  local -a raw_times=()
  local -a raw_sizes=()

  if test -n "$single_machine"; then
    # find dir in _tmp/ovm-build
    local -a a=( $base_dir/raw.$single_machine.* )

    raw_times+=( ${a[-1]}/times.tsv )
    raw_sizes+=( ${a[-1]}/native-sizes.tsv )

  else
    # find last dirs in ../benchmark-data/ovm-build
    # Globs are in lexicographical order, which works for our dates.
    local -a a=( $base_dir/raw.$MACHINE1.* )
    local -a b=( $base_dir/raw.$MACHINE2.* )

    raw_times+=( ${a[-1]}/times.tsv ${b[-1]}/times.tsv )
    raw_sizes+=( ${a[-1]}/native-sizes.tsv ${b[-1]}/native-sizes.tsv )
  fi

  tsv-concat "${raw_times[@]}" > $out_dir/times.tsv
  tsv-concat "${raw_sizes[@]}" > $out_dir/native-sizes.tsv

  return

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
      <a href="/">oils.pub</a>
    </p>
EOF

  cmark << 'EOF'
## OVM Build Performance

Source code: [oil/benchmarks/osh-parser.sh](https://github.com/oilshell/oil/tree/master/benchmarks/osh-parser.sh)

### Time in Seconds by Host and Compiler

We measure the build speed of `bash` and `dash` for comparison.
EOF

  # Highlighting clang makes this table easier to read.
  tsv2html \
    --css-class-pattern 'special ^gcc' \
    $in_dir/times.tsv

  cmark << 'EOF'
### Native Binary Size

EOF
  tsv2html --css-class-pattern 'special ^gcc' $in_dir/native-sizes.tsv

  cmark << 'EOF'

### Host and Compiler Details
EOF
  tsv2html $in_dir/hosts.tsv
  tsv2html $in_dir/compilers.tsv

  cat <<EOF
  </body>
</html>
EOF
}

soil-run() {
  rm -r -f $BASE_DIR
  mkdir -p $BASE_DIR

  download
  extract-other

  # Copied from benchmarks/osh-runtime.sh soil-run

  # could add _bin/cxx-bumpleak/oils-for-unix, although sometimes it's slower
  local -a osh_bin=( $OSH_CPP_NINJA_BUILD )
  ninja "${osh_bin[@]}"

  local single_machine='no-host'

  local single_machine='no-host'

  local job_id
  job_id=$(print-job-id)

  compiler-provenance-2 \
    $single_machine $job_id _tmp

  local host_job_id="$single_machine.$job_id"
  local raw_out_dir="$BASE_DIR/raw.$host_job_id"
  mkdir -p $raw_out_dir $BASE_DIR/stage1

  measure _tmp/compiler-provenance.txt $raw_out_dir

  # Trivial concatenation for 1 machine
  stage1 '' $single_machine

  benchmarks/report.sh stage2 $BASE_DIR

  benchmarks/report.sh stage3 $BASE_DIR
}

"$@"

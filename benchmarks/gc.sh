#!/usr/bin/env bash
#
# Usage:
#   benchmarks/gc.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)

source benchmarks/common.sh  # benchmark-html-head
source test/common.sh  # R_PATH
source test/tsv-lib.sh

readonly BASE_DIR=_tmp/gc

# See benchmarks/gperftools.sh.  I think the Ubuntu package is very old

download-tcmalloc() {
  # TODO: move this to ../oil_DEPS ?
  wget --directory _deps \
    https://github.com/gperftools/gperftools/releases/download/gperftools-2.10/gperftools-2.10.tar.gz

  # Then ./configure; make; sudo make install
  # installs in /usr/local/lib

  # Note: there's a warning about libunwind -- maybe install that first.  Does
  # it only apply to CPU profiles?
}

debug-tcmalloc() {
  touch mycpp/marksweep_heap.cc

  # No evidence of difference
  for bin in _bin/cxx-{opt,tcmalloc}/osh_eval; do
    echo $bin
    ninja $bin

    ldd $bin
    echo

    ls -l $bin
    echo

    # Check what we're linking against
    nm $bin | egrep -i 'malloc|calloc'
    #wc -l
    echo
  done
}

install-m32() {
  # needed to compile with -m32
  sudo apt install gcc-multilib g++-multilib
}

max-rss() {
  # %e is real time
  /usr/bin/time --format '%e %M' -- "$@"
}

compare-m32() {
  for bin in _bin/cxx-opt{,32}/osh_eval.stripped; do
    echo $bin
    ninja $bin

    ldd $bin
    echo

    file $bin
    echo

    ls -l $bin
    echo

    # 141136 KiB vs. 110924 KiB.  Significant savings, but it's slower.
    max-rss $bin --ast-format none -n benchmarks/testdata/configure-coreutils

  done
}

banner() {
  echo -----
  echo "$@"
}

readonly TAB=$'\t'

print-tasks() {
  local workload='parse.configure-coreutils'
  local -a rows=( $workload"$TAB"{bash,dash,zsh,osh-{1,2,3,4,5}} )

  local -a workloads=(
    parse.configure-coreutils
    parse.abuild
    ex.bashcomp-parse-help  # only runs with bash
    ex.abuild-print-help  # bash / dash / zsh
    ex.compute-fib  # bash / dash / zsh
  )

  local -a shells=(
    "bash$TAB-"
    "dash$TAB-"
    "zsh$TAB-"

    "_bin/cxx-bumpleak/osh_eval${TAB}mut"
    # these have trivial GC stats
    "_bin/cxx-opt/osh_eval${TAB}mut+alloc"
    "_bin/cxx-opt/osh_eval${TAB}mut+alloc+free"
    # good GC stats
    "_bin/cxx-opt/osh_eval${TAB}mut+alloc+free+gc"
    "_bin/cxx-opt/osh_eval${TAB}mut+alloc+free+gc+exit"
  )

  local id=0

  for workload in "${workloads[@]}"; do
    for shell in "${shells[@]}"; do
      local row_part="$workload${TAB}$shell"

      # Skip these rows
      case $row_part in
        "ex.bashcomp-parse-help${TAB}dash"*)
          continue
          ;;
        "ex.bashcomp-parse-help${TAB}zsh"*)
          continue
          ;;
      esac

      local join_id="gc$id"
      local row="$join_id${TAB}$row_part"
      echo "$row"

      id=$((id + 1))


    done
  done
}

readonly BIG_THRESHOLD=$(( 1 * 1000 * 1000 * 1000 ))  # 1 B

run-tasks() {
  while read -r join_id task shell_bin shell_runtime_opts; do

    # Parse two different files
    case $task in
      parse.configure-coreutils)
        data_file='benchmarks/testdata/configure-coreutils'
        ;;
      parse.abuild)
        data_file='benchmarks/testdata/abuild'
        ;;
    esac

    # Construct argv for each task
    local -a argv
    case $task in
      parse.*)
        argv=( -n $data_file )

        case $shell_bin in
          */osh_eval)
            argv=( --ast-format none "${argv[@]}" )
            ;;
        esac
        ;;

      ex.bashcomp-parse-help)
        argv=( benchmarks/parse-help/pure-excerpt.sh parse_help_file 
               benchmarks/parse-help/clang.txt )
        ;;

      ex.abuild-print-help)
        argv=( testdata/osh-runtime/abuild -h )
        ;;

      ex.compute-fib)
        argv=( benchmarks/compute/fib.sh 100 44 )
        ;;

      *)
        die "Invalid task $task"
        ;;
    esac

    echo $join_id $task $shell_bin $shell_runtime_opts

    argv=( $shell_bin "${argv[@]}" )
    #echo + "${argv[@]}"
    #set -x

    # Wrap in a command that writes one row of a TSV
    local -a time_argv=(
      time-tsv -o $tsv_out --append 
      --rusage
      --field "$join_id" --field "$task" --field "$shell_bin" --field "$shell_runtime_opts"
      -- "${argv[@]}"
    )

    # Run with the right environment variables

    case $shell_runtime_opts in 
      -)
        "${time_argv[@]}" > /dev/null
        ;;
      mut)
        OIL_GC_STATS=1 \
          "${time_argv[@]}" > /dev/null
        ;;
      mut+alloc)
        # disable GC with big threshold
        OIL_GC_STATS=1 OIL_GC_THRESHOLD=$BIG_THRESHOLD \
          "${time_argv[@]}" > /dev/null
        ;;
      mut+alloc+free)
        # do a single GC on exit
        OIL_GC_STATS=1 OIL_GC_THRESHOLD=$BIG_THRESHOLD OIL_GC_ON_EXIT=1 \
          "${time_argv[@]}" > /dev/null
        ;;
      mut+alloc+free+gc)
        # default configuration
        OIL_GC_STATS=1 \
          "${time_argv[@]}" > /dev/null
        ;;
      mut+alloc+free+gc+exit)
        # also GC on exit
        OIL_GC_STATS=1 OIL_GC_ON_EXIT=1 \
          "${time_argv[@]}" > /dev/null
        ;;

      # More comparisons:
      # - tcmalloc,
      # - 32-bit 
      # - different GC thresholds

      *)
        die "Invalid shell runtime opts $shell_runtime_opts"
        ;;
    esac

  done

  # TODO: OIL_GC_STATS_FD and tsv_column_from_files.py
}

# This is how OIL_GC_STATS_FD=99 will work?

fd-demo() {
  local fd=99

  # Hm you can't do $fd>out.txt, but that's OK

  FD=$fd 99>out.txt python -c '
import os
fd = int(os.getenv("FD"))
os.write(fd, "hello\n")
os.write(fd, "world\n")
  '

  ls -l out.txt
  cat out.txt
}

more-variants() {
  # TODO: could revive this

  case $compare_more in
    (*m32*)
      # Surprisingly, -m32 is SLOWER, even though it allocates less.
      # My guess is because less work is going into maintaining this code path in
      # GCC.

      # 223 ms
      # 61.9 MB bytes allocated
      local bin=_bin/cxx-opt32/osh_eval
      OIL_GC_THRESHOLD=$big_threshold \
        run-osh $tsv_out $bin 'm32 mutator+malloc' $file

      # 280 ms
      OIL_GC_STATS=1 \
        run-osh $tsv_out $bin 'm32 mutator+malloc+free+gc' $file
      ;;
  esac

  case $compare_more in
    (*tcmalloc*)

      # 184 ms
      local tcmalloc_bin=_bin/cxx-tcmalloc/osh_eval
      OIL_GC_THRESHOLD=$big_threshold \
        run-osh $tsv_out $tcmalloc_bin 'mutator+tcmalloc' $file

      # Faster: 218 ms!  It doesn't have the huge free() penalty that glibc does.
      # Maybe it doesn't do all the malloc_consolidate() stuff.
      OIL_GC_STATS=1 \
        run-osh $tsv_out $tcmalloc_bin 'mutator+tcmalloc+free+gc' $file
      ;;
  esac

  # Show log of GC
  case $compare_more in
    (*gcverbose*)
      local bin=_bin/cxx-gcverbose/osh_eval
      # 280 ms
      OIL_GC_STATS=1 OIL_GC_ON_EXIT=1 \
        run-osh $tsv_out $bin 'gcverbose mutator+malloc+free+gc' $file
      ;;
  esac

  if command -v pretty-tsv; then
    pretty-tsv $tsv_out
  fi
}

measure-all() {
  ninja _bin/cxx-{bumpleak,opt}/osh_eval

  local tsv_out=${1:-$BASE_DIR/raw/times.tsv}
  mkdir -p $(dirname $tsv_out)

  # Make the header
  time-tsv -o $tsv_out --print-header \
    --rusage --field join_id --field task --field shell_bin --field shell_runtime_opts

  time print-tasks | run-tasks $tsv_out

  if command -v pretty-tsv; then
    pretty-tsv $tsv_out
  fi
}

print-report() {
  local in_dir=$1

  benchmark-html-head 'Memory Management Overhead'

  cat <<EOF
  <body class="width60">
    <p id="home-link">
      <a href="/">oilshell.org</a>
    </p>
EOF

  cmark << 'EOF'
## Memory Management Overhead

Source code: [oil/benchmarks/gc.sh](https://github.com/oilshell/oil/tree/master/benchmarks/gc.sh)

### Comparison

Parsing a big file, like in the [parser benchmark](../osh-parser/index.html).

EOF

  tsv2html $in_dir/times.tsv

  cat <<EOF
  </body>
</html>
EOF
}

soil-run() {
  measure-all

  mkdir -p $BASE_DIR/stage2
  R_LIBS_USER=$R_PATH benchmarks/report.R gc $BASE_DIR/raw $BASE_DIR/stage2

  benchmarks/report.sh stage3 $BASE_DIR
}

#
# Misc Tests
#


gc-parse-smoke() {
  local variant=${1:-opt}

  local bin=_bin/cxx-$variant/osh_eval
  ninja $bin

  _OIL_GC_VERBOSE=1 OIL_GC_STATS=1 OIL_GC_THRESHOLD=1000 OIL_GC_ON_EXIT=1 \
    $bin -n configure

  # No leaks
  # OIL_GC_STATS=1 OIL_GC_THRESHOLD=1000 OIL_GC_ON_EXIT=1 $bin -n -c '('
}

gc-run-smoke() {
  local variant=${1:-opt}

  local bin=_bin/cxx-$variant/osh_eval
  ninja $bin

  # expose a bug with printf
  _OIL_GC_VERBOSE=1 OIL_GC_STATS=1 OIL_GC_THRESHOLD=500 OIL_GC_ON_EXIT=1 \
    $bin -c 'for i in $(seq 100); do printf "%s\\n" "-- $i"; done'
}

gc-run-oil() {
  ### Run some scripts from the repo

  local variant=${1:-opt}

  local bin=_bin/cxx-$variant/osh_eval
  ninja $bin

  local i=0
  for script in */*.sh; do
    case $script in
      (build/clean.sh|build/common.sh|build/dev.sh)
        # Top level does something!
        echo "=== SKIP $script"
        continue
        ;;
    esac

    echo
    echo "=== ($i) $script"

    # Just run the top level, which (hopefully) does nothing
    _OIL_GC_VERBOSE=1 OIL_GC_STATS=1 OIL_GC_THRESHOLD=1000 OIL_GC_ON_EXIT=1 \
      $bin $script

    i=$((i + 1))
    if test $i -gt 60; then
      break
    fi
  done
}

gc-run-big() {
  local variant=${1:-opt}

  local target=_bin/cxx-$variant/osh_eval
  ninja $target

  local osh=$REPO_ROOT/$target

  local dir=_tmp/gc-run-big
  rm -r -f -v $dir
  mkdir -v -p $dir

  pushd $dir
  time _OIL_GC_VERBOSE=1 OIL_GC_STATS=1 OIL_GC_THRESHOLD=100000 OIL_GC_ON_EXIT=1 \
    $osh ../../Python-2.7.13/configure
  popd
}


"$@"

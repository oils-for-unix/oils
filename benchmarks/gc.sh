#!/usr/bin/env bash
#
# Usage:
#   benchmarks/gc.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)

source benchmarks/common.sh  # benchmark-html-head
source benchmarks/cachegrind.sh  # with-cachegrind
source build/dev-shell.sh  # R_LIBS_USER
source test/tsv-lib.sh

readonly BASE_DIR=_tmp/gc

# duplicated in benchmarks/gc-cachegrind.sh
readonly BASE_DIR_CACHEGRIND=_tmp/gc-cachegrind

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
  for bin in _bin/cxx-{opt,opt+tcmalloc}/osh; do
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
  sudo apt-get install gcc-multilib g++-multilib
}

max-rss() {
  # %e is real time
  /usr/bin/time --format '%e %M' -- "$@"
}

compare-m32() {
  for bin in _bin/cxx-opt{,32}/osh; do
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

print-tasks() {
  local mycpp_souffle=${1:-}

  local -a workloads=(
    parse.configure-coreutils
    parse.configure-cpython
    parse.abuild
    ex.bashcomp-parse-help  # only runs with bash
    ex.abuild-print-help  # bash / dash / zsh
    ex.compute-fib  # bash / dash / zsh
  )

  local -a shells=(
    "bash$TAB-"
    "dash$TAB-"
    "zsh$TAB-"

    "_bin/cxx-opt+bumpleak/osh${TAB}mut"
    "_bin/cxx-opt+bumproot/osh${TAB}mut"

    "_bin/cxx-opt+bumpsmall/osh${TAB}mut+alloc"
    "_bin/cxx-opt+nopool/osh${TAB}mut+alloc"
    "_bin/cxx-opt+nopool/osh${TAB}mut+alloc+free+gc"

    # these have trivial GC stats
    "_bin/cxx-opt/osh${TAB}mut+alloc"
    "_bin/cxx-opt/osh${TAB}mut+alloc+free"
    # good GC stats
    "_bin/cxx-opt/osh${TAB}mut+alloc+free+gc"
    "_bin/cxx-opt/osh${TAB}mut+alloc+free+gc+exit"
  )

  if test -n "$mycpp_souffle"; then
    shells+=(
      "_bin/cxx-opt/mycpp-souffle/osh${TAB}mut+alloc"
      "_bin/cxx-opt/mycpp-souffle/osh${TAB}mut+alloc+free"
      "_bin/cxx-opt/mycpp-souffle/osh${TAB}mut+alloc+free+gc"
      "_bin/cxx-opt/mycpp-souffle/osh${TAB}mut+alloc+free+gc+exit"
    )
  fi

  if test -n "${TCMALLOC:-}"; then
    shells+=(
      "_bin/cxx-opt+tcmalloc/osh${TAB}mut+alloc"
      "_bin/cxx-opt+tcmalloc/osh${TAB}mut+alloc+free"
      "_bin/cxx-opt+tcmalloc/osh${TAB}mut+alloc+free+gc"
    )
  fi

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

      local join_id="gc-$id"
      local row="$join_id${TAB}$row_part"
      echo "$row"

      id=$((id + 1))

    done

    # Run a quick 10 tasks
    if test -n "${QUICKLY:-}" && test $id -gt 10; then
      break
    fi
  done
}

print-cachegrind-tasks() {
  local mycpp_souffle=${1:-}

  local -a workloads=(
    # coreutils is on osh-parser
    #parse.configure-coreutils

    #parse.configure-cpython

    # Faster tasks, like benchmarks/uftrace, which is instrumented
    parse.abuild
    ex.compute-fib
  )

  local -a shells=(
    "bash${TAB}-"
    "_bin/cxx-opt+bumpleak/osh${TAB}mut"
    "_bin/cxx-opt+bumproot/osh${TAB}mut"

    "_bin/cxx-opt+bumpsmall/osh${TAB}mut+alloc"
    "_bin/cxx-opt+nopool/osh${TAB}mut+alloc"
    "_bin/cxx-opt+nopool/osh${TAB}mut+alloc+free+gc"

    "_bin/cxx-opt/osh${TAB}mut+alloc"
    "_bin/cxx-opt/osh${TAB}mut+alloc+free"
    "_bin/cxx-opt/osh${TAB}mut+alloc+free+gc"
    "_bin/cxx-opt/osh${TAB}mut+alloc+free+gc+exit"
  )

  if test -n "$mycpp_souffle"; then
    shells+=(
      "_bin/cxx-opt/mycpp-souffle/osh${TAB}mut+alloc"
      "_bin/cxx-opt/mycpp-souffle/osh${TAB}mut+alloc+free"
      "_bin/cxx-opt/mycpp-souffle/osh${TAB}mut+alloc+free+gc"
      "_bin/cxx-opt/mycpp-souffle/osh${TAB}mut+alloc+free+gc+exit"
    )
  fi

  local id=0
  for workload in "${workloads[@]}"; do
    for shell in "${shells[@]}"; do
      local row_part="$workload${TAB}$shell"

      local join_id="cachegrind-$id"
      local row="$join_id${TAB}$row_part"
      echo "$row"

      id=$((id + 1))
    done
  done
  #print-tasks | egrep 'configure-coreutils' | egrep osh
}


readonly BIG_THRESHOLD=$(( 1 * 1000 * 1000 * 1000 ))  # 1 B

run-tasks() {
  local tsv_out=$1
  local mode=${2:-time}

  while read -r join_id task sh_path shell_runtime_opts; do

    # Parse different files
    case $task in
      parse.configure-coreutils)
        data_file='benchmarks/testdata/configure-coreutils'
        ;;
      parse.configure-cpython)
        data_file='Python-2.7.13/configure'
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

        case $sh_path in
          _bin/*/osh)
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
        # fewer iterations when instrumented
        local iters
        if test $mode = time; then
          iters=100
        else
          iters=10
        fi

        argv=( benchmarks/compute/fib.sh $iters 44 )
        ;;

      *)
        die "Invalid task $task"
        ;;
    esac

    echo $join_id $task $sh_path $shell_runtime_opts

    argv=( $sh_path "${argv[@]}" )
    #echo + "${argv[@]}"
    #set -x

    if test $mode = cachegrind; then
      # Add prefix
      argv=( $0 with-cachegrind $BASE_DIR_CACHEGRIND/raw/$join_id.txt "${argv[@]}" )
    fi

    # Wrap in a command that writes one row of a TSV
    # Note: for cachegrind, we need the join ID, but the --rusage is meaningless
    local -a instrumented=(
      time-tsv -o $tsv_out --append 
        --rusage
        --field "$join_id" --field "$task" --field "$sh_path"
        --field "$shell_runtime_opts"
        -- "${argv[@]}"
    )

    # Run with the right environment variables

    case $shell_runtime_opts in 
      -)
        "${instrumented[@]}" > /dev/null
        ;;
      mut)
        OILS_GC_STATS=1 \
          "${instrumented[@]}" > /dev/null
        ;;
      mut+alloc)
        # disable GC with big threshold
        OILS_GC_STATS=1 OILS_GC_THRESHOLD=$BIG_THRESHOLD \
          "${instrumented[@]}" > /dev/null
        ;;
      mut+alloc+free)
        # do a single GC on exit
        OILS_GC_STATS=1 OILS_GC_THRESHOLD=$BIG_THRESHOLD OILS_GC_ON_EXIT=1 \
          "${instrumented[@]}" > /dev/null
        ;;
      mut+alloc+free+gc)
        # Default configuration
        #
        # Save the GC stats here.  None of the other runtime options are that
        # interesting.

        if test $mode = 'time' && test $sh_path != _bin/cxx-opt+nopool/osh; then
          OILS_GC_STATS_FD=99 \
            "${instrumented[@]}" > /dev/null 99>$BASE_DIR/raw/$join_id.txt
        else
          "${instrumented[@]}" > /dev/null
        fi
        ;;
      mut+alloc+free+gc+exit)
        # also GC on exit
        OILS_GC_STATS=1 OILS_GC_ON_EXIT=1 \
          "${instrumented[@]}" > /dev/null
        ;;

      *)
        die "Invalid shell runtime opts $shell_runtime_opts"
        ;;
    esac

  done

  # TODO: OILS_GC_STATS_FD and tsv_column_from_files.py
}

fd-demo() {
  local out=_tmp/gc/demo.txt

  local bin=_bin/cxx-dbg/oils-for-unix
  ninja $bin

  # Hm you can't do $fd>out.txt, but that's OK
  local fd=99

  OILS_GC_STATS_FD=$fd 99>$out \
    $bin --ast-format none -n benchmarks/testdata/configure

  ls -l $out
  cat $out
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
      local bin=_bin/cxx-opt32/oils-for-unix
      OILS_GC_THRESHOLD=$big_threshold \
        run-osh $tsv_out $bin 'm32 mutator+malloc' $file

      # 280 ms
      OILS_GC_STATS=1 \
        run-osh $tsv_out $bin 'm32 mutator+malloc+free+gc' $file
      ;;
  esac

  # Show log of GC
  case $compare_more in
    (*gcverbose*)
      local bin=_bin/cxx-gcverbose/oils-for-unix
      # 280 ms
      OILS_GC_STATS=1 OILS_GC_ON_EXIT=1 \
        run-osh $tsv_out $bin 'gcverbose mutator+malloc+free+gc' $file
      ;;
  esac

  if command -v pretty-tsv; then
    pretty-tsv $tsv_out
  fi
}

build-binaries() {
  if true; then

    soil/cpp-tarball.sh build-like-ninja \
      opt{,+bumpleak,+bumproot,+bumpsmall,+nopool}

    OILS_TRANSLATOR=mycpp-souffle soil/cpp-tarball.sh build-like-ninja opt

  else

    # Old Ninja build
    local -a bin=( _bin/cxx-opt{,+bumpleak,+bumproot,+bumpsmall,+nopool}/osh )
    bin+=( _bin/cxx-opt/mycpp-souffle/osh )

    if test -n "${TCMALLOC:-}"; then
      bin+=( _bin/cxx-opt+tcmalloc/osh )
    fi
    ninja "${bin[@]}"
  fi
}

measure-all() {
  local tsv_out=${1:-$BASE_DIR/raw/times.tsv}
  local mycpp_souffle=${2:-}

  build-binaries

  mkdir -p $(dirname $tsv_out)

  # Make the header
  time-tsv -o $tsv_out --print-header \
    --rusage --field join_id --field task --field sh_path --field shell_runtime_opts

  # Pass through args, which may include mycpp-souffle
  time print-tasks "$mycpp_souffle" | run-tasks $tsv_out

  if command -v pretty-tsv; then
    pretty-tsv $tsv_out
  fi
}

measure-cachegrind() {
  local tsv_out=${1:-$BASE_DIR_CACHEGRIND/raw/times.tsv}
  local mycpp_souffle=${2:-}

  build-binaries

  mkdir -p $(dirname $tsv_out)

  # Make the header
  time-tsv -o $tsv_out --print-header \
    --rusage --field join_id --field task --field sh_path --field shell_runtime_opts

  print-cachegrind-tasks "$mycpp_souffle" | run-tasks $tsv_out cachegrind

  # TODO: join cachegrind columns

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
EOF

  cmark << 'EOF'
### GC Stats

EOF

  tsv2html $in_dir/gc_stats.tsv

  cmark << 'EOF'

- Underlying data: [stage2/gc_stats.tsv](stage2/gc_stats.tsv)
- More columns: [stage1/gc_stats.tsv](stage1/gc_stats.tsv)

### Resource Usage

#### parse.configure-cpython

EOF

  tsv2html $in_dir/parse.configure-cpython.tsv

  cmark << 'EOF'
#### parse.configure-coreutils

Parsing the autoconf-generated `configure` script from GNU coreutils.

Note that unlike other shells, `osh -n` retains all nodes on purpose.  (See the
[parser benchmark](../osh-parser/index.html)).

EOF

  tsv2html $in_dir/parse.configure-coreutils.tsv

  cmark <<'EOF'
#### parse.abuild

Parsing `abuild` from Alpine Linux.
EOF

  tsv2html $in_dir/parse.abuild.tsv

  cmark <<'EOF'
#### ex.compute-fib

A synthetic benchmark for POSIX shell arithmetic.
EOF

  tsv2html $in_dir/ex.compute-fib.tsv

  cmark <<'EOF'
#### ex.bashcomp-parse-help

A realistic `bash-completion` workload.
EOF

  tsv2html $in_dir/ex.bashcomp-parse-help.tsv

  cmark <<'EOF'
#### ex.abuild-print-help

Running `abuild -h` from Alpine Linux.

EOF

  tsv2html $in_dir/ex.abuild-print-help.tsv

  cmark << 'EOF'
- Underlying data: [stage2/times.tsv](stage2/times.tsv)
EOF

  cat <<EOF

  </body>
</html>
EOF
}

make-report() {
  mkdir -p $BASE_DIR/{stage1,stage2}

  # Concatenate tiny files
  benchmarks/gc_stats_to_tsv.py $BASE_DIR/raw/gc-*.txt \
    > $BASE_DIR/stage1/gc_stats.tsv

  # Make TSV files
  benchmarks/report.R gc $BASE_DIR $BASE_DIR/stage2

  # Make HTML
  benchmarks/report.sh stage3 $BASE_DIR
}

soil-run() {
  ### Run in soil/benchmarks

  measure-all '' mycpp-souffle

  make-report
}

run-for-release() {
  measure-all ''

  make-report
}

#
# Misc Tests
#

gc-parse-smoke() {
  local variant=${1:-opt}
  local file=${2:-configure}

  local bin=_bin/cxx-$variant/osh
  ninja $bin

  # OILS_GC_THRESHOLD=1000 OILS_GC_ON_EXIT=1 \
  time _OILS_GC_VERBOSE=1 OILS_GC_STATS=1 \
    $bin --ast-format none -n $file

  # No leaks
  # OILS_GC_STATS=1 OILS_GC_THRESHOLD=1000 OILS_GC_ON_EXIT=1 $bin -n -c '('
}

gc-parse-big() {
  local variant=${1:-opt}

  gc-parse-smoke $variant benchmarks/testdata/configure-coreutils
}

gc-run-smoke() {
  local variant=${1:-opt}

  local bin=_bin/cxx-$variant/oils-for-unix
  ninja $bin

  # expose a bug with printf
  _OILS_GC_VERBOSE=1 OILS_GC_STATS=1 OILS_GC_THRESHOLD=500 OILS_GC_ON_EXIT=1 \
    $bin -c 'for i in $(seq 100); do printf "%s\\n" "-- $i"; done'
}

gc-run-oil() {
  ### Run some scripts from the repo

  local variant=${1:-opt}

  local bin=_bin/cxx-$variant/oils-for-unix
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
    _OILS_GC_VERBOSE=1 OILS_GC_STATS=1 OILS_GC_THRESHOLD=1000 OILS_GC_ON_EXIT=1 \
      $bin $script

    i=$((i + 1))
    if test $i -gt 60; then
      break
    fi
  done
}

gc-run-big() {
  local variant=${1:-opt}

  local target=_bin/cxx-$variant/oils-for-unix
  ninja $target

  local osh=$REPO_ROOT/$target

  local dir=_tmp/gc-run-big
  rm -r -f -v $dir
  mkdir -v -p $dir

  pushd $dir
  time _OILS_GC_VERBOSE=1 OILS_GC_STATS=1 OILS_GC_THRESHOLD=100000 OILS_GC_ON_EXIT=1 \
    $osh ../../Python-2.7.13/configure
  popd
}

run-verbose() {
  _OILS_GC_VERBOSE=1 OILS_GC_STATS=1 \
    /usr/bin/time --format '*** MAX RSS KiB = %M' -- \
    "$@"
}

# This hit the 24-bit object ID limitation in 2.5 seconds
# Should be able to run indefinitely.
run-for-a-long-time() {
  local bin=_bin/cxx-opt/osh
  ninja $bin
  run-verbose $bin benchmarks/compute/fib.sh 10000

  # time _OILS_GC_VERBOSE=1 OILS_GC_STATS=1 _bin/cxx-opt/osh benchmarks/compute/fib.sh 10000
}

while-loop() {
  local i=0
  while test $i -lt 10000; do
    if ((i % 1000 == 0)) ; then
      echo $i
    fi
    i=$((i + 1))
    continue  # BUG: skipped GC point
  done
}

for-loop() {
  for i in $(seq 10000); do
    if ((i % 1000 == 0)) ; then
      echo $i
    fi
    continue
  done
}

recurse() {
  local n=${1:-3000}

  if ((n % 100 == 0)) ; then
    echo $n
  fi

  if test $n = 0; then
    return
  fi

  recurse $((n - 1))
}

test-loops() {
  ### Regression for leak

  local bin=_bin/cxx-opt/osh
  ninja $bin

  run-verbose $bin $0 recurse
  echo

  run-verbose $bin $0 while-loop
  echo

  run-verbose $bin $0 for-loop
}

expand-loop() {
  local n=$1

  local bin=_bin/cxx-opt/osh
  ninja $bin

  set -x
  time _OILS_GC_VERBOSE=1 OILS_GC_STATS=1 \
    $bin -c "for i in {1..$n}; do echo \$i; done > /dev/null"
  set +x
}

test-brace-exp() {
  expand-loop 330000
  expand-loop 340000
}

"$@"

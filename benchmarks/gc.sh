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

# Table column:
#
# - status elapsed user sys max_rss_KiB
# - shell (with variant) 
# - comment (OIL_GC_ON_EXIT, OIL_GC_THRESHOLD)
# - TODO: can also add the file parsed

table-row() {
  local out=$1
  local shell=$2
  local comment=$3
  shift 3

  banner "  time-tsv $shell / $comment"

  # TODO: add --verbose to show a message on stderr?
  time-tsv -o $out --append \
    --rusage --field "$shell" --field "$comment" -- "$@"
}

table-header() {
  local out=$1
  time-tsv -o $out --print-header \
    --rusage --field shell --field comment
}

run-osh() {
  local tsv_out=$1
  local bin=$2
  local comment=$3
  local file=$4

  ninja $bin

  table-row $tsv_out $bin $comment \
    $bin --ast-format none -n $file
}

# TODO:
# - integrate with benchmarks/gperftools.sh, and measure memory usage

parser-compare() {
  local tsv_out=${1:-$BASE_DIR/raw/parser.tsv}
  local file=${2:-benchmarks/testdata/configure-coreutils}

  mkdir -p $(dirname $tsv_out)

  table-header $tsv_out

  local no_comment='-'

  # ~50ms
  table-row $tsv_out dash $no_comment \
    dash -n $file
  echo

  # 91 ms
  table-row $tsv_out bash $no_comment \
    bash -n $file
  echo

  # 274 ms
  table-row $tsv_out zsh $no_comment \
    zsh -n $file
  echo

  # ~88 ms!  But we are using more system time than bash/dash -- it's almost
  # certainly UNBUFFERED line-based I/O!
  local bin=_bin/cxx-bumpleak/osh_eval
  OIL_GC_STATS=1 run-osh $tsv_out $bin 'mutator' $file
  echo

  # 165 ms
  local bin=_bin/cxx-mallocleak/osh_eval
  run-osh $tsv_out $bin 'mutator+mallocleak' $file

  # 184 ms
  # Garbage-collected Oil binary
  local bin=_bin/cxx-opt/osh_eval
  OIL_GC_STATS=1 run-osh $tsv_out $bin 'mutator+malloc' $file

  # 277 ms -- free() is slow
  OIL_GC_STATS=1 OIL_GC_ON_EXIT=1 run-osh $tsv_out $bin 'mutator+malloc+free' $file

  # Enable GC with low GC threshold
  # Note: The parsing case won't show up because main_loop.ParseWholeFile() retains all nodes
  OIL_GC_THRESHOLD=1000 OIL_GC_ON_EXIT=1 run-osh $tsv_out $bin 'mutator+malloc+free+gc' $file

  if false; then
    # Surprisingly, -m32 is SLOWER, even though it allocates less.
    # My guess is because less work is going into maintaining this code path in
    # GCC.

    # 223 ms
    # 61.9 MB bytes allocated
    banner 'OPT32 - malloc only'
    local bin=_bin/cxx-opt32/osh_eval
    run-osh $bin

    # 280 ms
    banner 'OPT32 GC on exit - malloc + free'
    OIL_GC_STATS=1 OIL_GC_ON_EXIT=1 run-osh $bin
  fi

  if false; then
    # 184 ms
    banner 'tcmalloc - malloc only'
    local tcmalloc_bin=_bin/cxx-tcmalloc/osh_eval
    run-osh $tcmalloc_bin

    # Faster: 218 ms!  It doesn't have the huge free() penalty that glibc does.
    # Maybe it doesn't do all the malloc_consolidate() stuff.
    banner 'tcmalloc GC on exit - malloc + free'
    OIL_GC_ON_EXIT=1 run-osh $tcmalloc_bin
  fi

  if command -v pretty-tsv; then
    pretty-tsv $tsv_out
  fi
}

parse-compare-two() {
  parser-compare ''

  # Similar, smaller file.  zsh is faster
  parser-compare '' benchmarks/testdata/configure

  #compare testdata/completion/git-completion.bash
  #compare testdata/osh-runtime/abuild
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

### Parser Comparison

Parsing a big file, like in the [parser benchmark](../osh-parser/index.html).

EOF

  tsv2html $in_dir/parser.tsv

  cat <<EOF
  </body>
</html>
EOF
}

soil-run() {
  parser-compare

  mkdir -p $BASE_DIR/stage2
  R_LIBS_USER=$R_PATH benchmarks/report.R gc $BASE_DIR/raw $BASE_DIR/stage2

  benchmarks/report.sh stage3 $BASE_DIR
}

"$@"

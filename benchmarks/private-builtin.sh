#!/usr/bin/env bash
#
# Test how fast it is
#
# Usage:
#   benchmarks/private-builtin.sh <function name>

set -o nounset
#set -o pipefail
set -o errexit

repeat_it() {
  local n=${1:-1000}
  shift

  local i=0
  while test $i -lt $n; do
    "$@"
    i=$(( i + 1 ))
  done
}

true_builtin() {
  repeat_it 1000 true
}

true_extern() {
  repeat_it 1000 /bin/true
}

my_time() {
  command time -f 'elapsed=%s user=%U sys=%S' "$@"
}

true_demo() {
  local sh=${1:-bash}

  # 2 ms
  echo builtin
  my_time $sh $0 true_builtin

  # lowest ash/dash/ksh/mksh: ~290ms-680 ms
  # bash: ~780 ms
  # highest osh: ~850-890 ms
  #
  # I bet this has to do with dynamic linking
  echo extern
  my_time $sh $0 true_extern
}

. build/dev-shell.sh

true_demo_all() {
  for sh in ash dash ksh mksh bash zsh osh; do
    echo "=== $sh"
    true_demo $sh
    echo
  done
}

cat_builtin() {
  #local n=${1:-1000}
  #shift
  local n=1000

  # 500 ms!
  # I want to speed this up.

  # Wow, doing it in bash is only 9 ms!
  # does bash not fork?

  # Why is it slower in OSH?

  local i=0
  local len=0
  while test $i -lt $n; do
    # this runs the __cat builtin
    # should it be optimized to do something else?

    local s=$( < _tmp/tiny)
    len=$(( len + ${#s} ))

    i=$(( i + 1 ))
  done
  echo len=$len
}

cat_extern() {
  local prefix=${1:-}

  # unquoted $prefix
  repeat_it 1000 $prefix cat _tmp/tiny
}

cat_demo() {
  local sh=${1:-bash}

  echo 'tiny file' > _tmp/tiny

  local prefix
  case $sh in 
    *osh) prefix=builtin ;;
    *) prefix='' ;;
  esac

  echo extern

  my_time $sh $0 cat_extern "$prefix" > /dev/null

  # This is really fast in bash zsh mksh ksh, and gives correct answer of 9000
  # as fast as builtin
  #
  # It's slow in OSH for some reason - forking?
  echo 'builtin $(<file)'
  my_time $sh $0 cat_builtin
}

cat_demo_all() {
  local osh=_bin/cxx-opt/osh
  ninja $osh

  for sh in bash mksh ksh zsh $osh; do
    echo "=== $sh"
    cat_demo $sh
    echo
  done
}

num_procs() {
  local dir=_tmp/priv

  # OSH should not fork!  Bad!
  rm -r -f $dir

  for sh in bash mksh ksh zsh osh; do
    local sh_dir=$dir/$sh
    mkdir -p $sh_dir
    strace -ff -o $sh_dir/trace -- $sh -c 's=$(<configure); echo ${#s}'
  done
  tree $dir
}

# TODO:
# - enable --private cat
# - and then maybe shopt --set optimize_extern
#   - top candidates: rm, cat, mv
#   - see benchmarks/autoconf.sh
#   - I think it will help, but not with autoconf: mkdir, mkdir -p

"$@"

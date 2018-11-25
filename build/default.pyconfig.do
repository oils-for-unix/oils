#!/usr/bin/env bash
exec >&2

redo-ifchange common.sh
. ./common.sh

base=$2
dir=../_devbuild/cpython-$base
if [ ! -e "$base.pyflags" ]; then
  die "missing $base.pyflags; can't build requested variant."
fi

rm -r -f $dir
mkdir -p $dir

conf=$PWD/../$PY27/configure
redo-ifchange $conf

pushd $dir 
time $conf --without-threads
redo-ifchange Makefile  # need to re-run if someone deletes this dir
popd

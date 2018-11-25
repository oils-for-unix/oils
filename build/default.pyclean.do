#!/usr/bin/env bash
exec >&2

redo-ifchange common.sh $2.pyconfig
source ./common.sh

base=$2
dir=../_devbuild/cpython-$base
if [ ! -e "$base.pyflags" ]; then
  die "missing $base.pyflags; can't build requested variant."
fi

# if build flags change, we'll need to recompile everything,
# so consider us needing a redo of the 'make clean' step.
redo-ifchange $base.pyflags

pushd $dir
make clean
popd

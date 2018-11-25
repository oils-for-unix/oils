#!/usr/bin/env bash
exec >&2

redo-ifchange common.sh $2.pyclean
source ./common.sh

base=$2
dir=../_devbuild/cpython-$base
if [ ! -e "$base.pyflags" ]; then
  die "missing $base.pyflags; can't build requested variant."
fi

# Clang makes this faster.  We have to build all modules so that we can
# dynamically discover them with py-deps.
#
# Takes about 27 seconds on a fast i7 machine.
# Ubuntu under VirtualBox on MacBook Air with 4 cores (3 jobs): 1m 25s with
# -O2, 30 s with -O0.  The Make part of the build is parallelized, but the
# setup.py part is not!

redo-ifchange $base.pyflags
read extra_cflags <$base.pyflags

pushd $dir
# Speed it up with -O0.
# NOTE: CFLAGS clobbers some Python flags, so use EXTRA_CFLAGS.

time make EXTRA_CFLAGS="$extra_cflags"
redo-ifchange python
popd

find "../$PY27" -name '*.[ch]' | xargs redo-ifchange

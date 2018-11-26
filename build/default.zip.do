#!/bin/bash
exec >&2

# Everything is relative to the repo root.
cd ..

redo-ifchange build/common.sh
. build/common.sh

app-deps() {
  local app_name=${1:-hello}
  local pythonpath=${2:-build/testdata}
  local main_module=${3:-hello}

  local prefix=_build/$app_name/app-deps

  # I need the right relative path for Oil
  ln -s -f $PWD/build/app_deps.py _tmp

  PYTHONPATH=$pythonpath \
    $PREPARE_DIR/python -S _tmp/app_deps.py both $main_module $prefix
}

normpath() {
  python -c '
import os, sys
for line in sys.stdin:
  line = line.strip()
  print(os.path.normpath(line))
'
}

make-zip() {
  REPO_ROOT=$PWD

  mkdir -p _build/oil

	# writes 2 files
	app-deps oil $REPO_ROOT bin.oil
	local pairs=_build/oil/app-deps-cpython.txt
	# Ignore these modules for now
	#cat _build/oil/app-deps-c.txt

	mkdir -p _build/oil-redo
  local out=_build/oil-redo/bytecode-opy.zip  
	build/make_zip.py $out < $pairs
	ls -l _build/oil-redo

  # Try fixing /../ in paths with normpath?  Doesn't seem to matter.

	awk '{print $1}' $pairs | normpath | xargs redo-ifchange
	redo-ifchange $out
}

make-zip

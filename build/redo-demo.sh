#!/bin/bash
#
# Usage:
#   ./redo-demo.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

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

make-zip() {
	REPO_ROOT=$(cd $(dirname $0)/.. && pwd)
	# writes 2 files
	app-deps oil $REPO_ROOT bin.oil
	local pairs=_build/oil/app-deps-cpython.txt
	# Ignore these modules for now
	#cat _build/oil/app-deps-c.txt

	mkdir -p _build/oil-redo
	build/make_zip.py _build/oil-redo/bytecode-opy.zip  < $pairs
	ls -l _build/oil-redo

	awk '{print $1}' $pairs | xargs redo-ifchange
}

"$@"

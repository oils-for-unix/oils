#!/usr/bin/env bash
#
# Translate parts of Oil with mycpp, to work around circular deps issue.
#
# Usage:
#   prebuilt/translate.sh <function name>

: ${LIB_OSH=stdlib/osh}
source $LIB_OSH/bash-strict.sh
source $LIB_OSH/task-five.sh

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)

source build/ninja-rules-cpp.sh

readonly TEMP_DIR=_build/tmp

oils-part() {
  ### Translate ASDL deps for unit tests

  local out_prefix=$1
  local raw_header=$2
  local guard=$3
  local more_include=$4
  shift 4

  local name=asdl_runtime
  local raw=$TEMP_DIR/${name}_raw.cc 

  mkdir -p $TEMP_DIR

  # j8_lite depends on pyext/fastfunc.pyi
  local mypypath=$REPO_ROOT:$REPO_ROOT/pyext

  local mycpp=_bin/shwrap/mycpp_main

  ninja $mycpp
  $mycpp \
    $mypypath $raw \
    --header-out $raw_header \
    "$@"

  { 
    echo "// $out_prefix.h: GENERATED by mycpp"
    echo
    echo "#ifndef $guard"
    echo "#define $guard"
    echo
    echo '#include "_gen/asdl/hnode.asdl.h"'
    echo '#include "_gen/display/pretty.asdl.h"'
    echo '#include "cpp/data_lang.h"'
    echo '#include "mycpp/runtime.h"'
    echo "$more_include"

    cat $raw_header

    echo "#endif  // $guard"

  } > $out_prefix.h

  { cat <<EOF
// $out_prefix.cc: GENERATED by mycpp

#include "$out_prefix.h"
EOF
    cat $raw

  } > $out_prefix.cc
}

readonly -a ASDL_FILES=(
  $REPO_ROOT/{asdl/runtime,asdl/format,display/ansi,display/pretty,pylib/cgi,data_lang/j8_lite}.py \
)

asdl-runtime() {
  mkdir -p prebuilt/asdl $TEMP_DIR/asdl
  oils-part \
    prebuilt/asdl/runtime.mycpp \
    $TEMP_DIR/asdl/runtime_raw.mycpp.h \
    ASDL_RUNTIME_MYCPP_H \
    '
#include "_gen/display/pretty.asdl.h"

using pretty_asdl::doc;  // ad hoc
      ' \
    --to-header asdl.runtime \
    --to-header asdl.format \
    "${ASDL_FILES[@]}"
}

core-error() {
  ### For cpp/osh_test.cc

  # Depends on frontend/syntax_asdl

  mkdir -p prebuilt/core $TEMP_DIR/core
  oils-part \
    prebuilt/core/error.mycpp \
    $TEMP_DIR/core/error.mycpp.h \
    CORE_ERROR_MYCPP_H \
    '
#include "_gen/core/runtime.asdl.h"
#include "_gen/core/value.asdl.h"
#include "_gen/frontend/syntax.asdl.h"

using value_asdl::value;  // This is a bit ad hoc
' \
    --to-header core.error \
    core/error.py \
    core/num.py
}

frontend-args() {
  ### For cpp/frontend_args_test.cc

  # Depends on core/runtime_asdl

  mkdir -p prebuilt/frontend $TEMP_DIR/frontend
  oils-part \
    prebuilt/frontend/args.mycpp \
    $TEMP_DIR/frontend/args_raw.mycpp.h \
    FRONTEND_ARGS_MYCPP_H \
    '
#include "_gen/core/runtime.asdl.h"
#include "_gen/core/value.asdl.h"
#include "_gen/display/pretty.asdl.h"
#include "_gen/frontend/syntax.asdl.h"
#include "cpp/frontend_flag_spec.h"

using value_asdl::value;  // This is a bit ad hoc
using pretty_asdl::doc;
' \
    --to-header asdl.runtime \
    --to-header asdl.format \
    --to-header frontend.args \
    "${ASDL_FILES[@]}" \
    core/error.py \
    core/num.py \
    frontend/args.py
}

all() {
  asdl-runtime
  core-error
  frontend-args
}

deps() {
  PYTHONPATH='.:vendor' \
    python2 -c 'import sys; from frontend import args; print(sys.modules.keys())'

  PYTHONPATH='.:vendor' \
    python2 -c 'import sys; from core import error; print(sys.modules.keys())'
}

task-five "$@"

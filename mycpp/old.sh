# old.sh: probably not using this stuff

# NOTE: Needs 'asdl/run.sh gen-cpp-demo' first
translate-compile-typed-arith() {
  # tdop.py is a dependency.  How do we determine order?
  #
  # I guess we should put them in arbitrary order.  All .h first, and then all
  # .cc first.

  # NOTE: tdop.py doesn't translate because of the RE module!

  local srcs=( $PWD/../asdl/tdop.py $PWD/../asdl/typed_arith_parse.py )

  local name=typed_arith_parse
  translate-ordered $name '#include "typed_arith.asdl.h"' "${srcs[@]}"

  cc -o _bin/$name $CPPFLAGS \
    -I . -I ../_tmp \
    _gen/$name.cc mylib.cc \
    -lstdc++
}

# NOT USED
modules-deps() {
  local main_module=modules
  local prefix=_tmp/modules

  # This is very hacky but works.  We want the full list of files.
  local pythonpath="$PWD:$PWD/examples:$(cd $PWD/../vendor && pwd)"

  pushd examples
  mkdir -p _tmp
  ln -s -f -v ../../../build/app_deps.py _tmp

  PYTHONPATH=$pythonpath \
    $PREPARE_DIR/python -S _tmp/app_deps.py both $main_module $prefix

  popd

  egrep '/mycpp/.*\.py$' examples/_tmp/modules-cpython.txt \
    | egrep -v '__init__.py|mylib.py' \
    | awk '{print $1}' > _tmp/manifest.txt

  local raw=_gen/modules_raw.cc
  local out=_gen/modules.cc

  cat _tmp/manifest.txt | xargs ./mycpp_main.py > $raw

  filter-cpp modules $raw > $out
  wc -l $raw $out
}

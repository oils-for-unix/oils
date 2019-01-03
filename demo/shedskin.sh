#!/bin/bash
#
# Usage:
#   ./shedskin.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

# Problems
# - loading pickle for metadata.  It has to dynamically look up classes.
# - it won't compile the pickle module due to its use of marshal!
# - TODO: we don't need metadata at all?

# Fixed
# - import posix removed in runtime.py
# - _CheckType uses AttributeError: Shed Skin doesn't like it

# Unfortunately the ShedSkin compiler crashes after 17 seconds with this error!
#
#     ts = typestrnew(gx, types, cplusplus, node, check_extmod, depth, check_ret, var, tuple_check, mv=mv)
#   File "/usr/lib/python2.7/dist-packages/shedskin/typestr.py", line 193, in typestrnew
#     elif not node or infer.inode(gx, node).mv.module.builtin:
# AttributeError: 'NoneType' object has no attribute 'module'
# 
# real    0m17.210s
# user    0m17.083s
# sys     0m0.084s


# 0.9.4 was released in 2015.  Supposedly fixed in git!
#
# https://github.com/shedskin/shedskin/issues/203

install-latest() {
  # NOTE: I manually transcribed what I did.  Could use virtualenv?
  pushd ~/git/languages/shedskin
  python setup.py build
  sudo python setup.py install
}

make-tree() {
  local out=_tmp/shedskin
  mkdir -p $out
  #cp -v asdl/{arith_parse.py,tdop.py} _devbuild/gen/demo_asdl.py $out

  # dependencies of generated code
  # unpickle probably won't work
  cp -v asdl/{const.py,runtime.py} $out
}

run-python() {
  pushd demo/shedskin
  ./arith_parse.py '1+2'
}

# With latest, this generates C++ code, but it doesn't compile.
#
# TODO: Try something based on tdop.py that is a single module?  There are too
# many modules here.

compile() {
  pushd demo/shedskin
  time shedskin arith_parse
}

count-output() {
  wc -l demo/shedskin/*.{cpp,hpp} Makefile
}

"$@"
